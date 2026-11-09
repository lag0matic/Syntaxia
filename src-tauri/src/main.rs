#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::{io::{BufRead,BufReader,Write},path::PathBuf,process::{Child,Command,Stdio},sync::{Arc,Mutex,Condvar,atomic::{AtomicBool,AtomicU64,Ordering}},time::{Duration,Instant}};
use std::os::windows::process::CommandExt;
use tauri::{Manager,WebviewWindow,WebviewWindowBuilder,WebviewUrl,WindowEvent,RunEvent};
use serde_json::{Value,json};

struct Runtime {
    child: Mutex<Child>, ack: Mutex<Option<Value>>, changed: Condvar,
    leaving: AtomicBool, allowed: AtomicBool, sequence: AtomicU64,
    catalog: PathBuf, database: PathBuf,
}
fn tell(text:&str) { rfd::MessageDialog::new().set_title("Syntaxia").set_description(text).show(); }
fn leave(window:WebviewWindow, runtime:Arc<Runtime>, closing:bool) {
    if runtime.leaving.swap(true,Ordering::SeqCst) { return; }
    let id=runtime.sequence.fetch_add(1,Ordering::SeqCst);
    *runtime.ack.lock().unwrap()=None;
    let code=format!("window.workshopDesktop?.requestLeave({id}, {closing})");
    let failed=window.eval(&code).is_err();
    std::thread::spawn(move || {
        let start=Instant::now();
        let mut ack=runtime.ack.lock().unwrap();
        while !failed && start.elapsed()<Duration::from_secs(10) && ack.as_ref().and_then(|v|v["request_id"].as_u64())!=Some(id) {
            ack=runtime.changed.wait_timeout(ack,Duration::from_millis(100)).unwrap().0;
        }
        let result=ack.take().unwrap_or(json!({"ok":false,"message":"The editor did not respond within ten seconds."}));
        drop(ack);
        let mut proceed=result["ok"].as_bool()==Some(true);
        if !proceed {
            let error=result["message"].as_str().unwrap_or("Could not confirm that your draft was saved.");
            if closing {
                proceed=rfd::MessageDialog::new().set_title("Close Syntaxia?")
                  .set_description(format!("{error}\n\nClose anyway? Unsaved edits may be lost. Choose No to copy or download your code first."))
                  .set_level(rfd::MessageLevel::Warning).set_buttons(rfd::MessageButtons::YesNo).show()==rfd::MessageDialogResult::Yes;
            } else { tell(error); }
        }
        if proceed {
            if closing { runtime.allowed.store(true,Ordering::SeqCst); let _=window.destroy(); }
            else { let _=window.eval("location.reload()"); }
        }
        runtime.leaving.store(false,Ordering::SeqCst);
    });
}
fn stop(runtime:&Runtime) {
    let mut child=runtime.child.lock().unwrap();
    if let Some(stdin)=child.stdin.as_mut() { let _=stdin.write_all(b"quit\n"); let _=stdin.flush(); }
    let start=Instant::now();
    while start.elapsed()<Duration::from_secs(3) {
        if matches!(child.try_wait(),Ok(Some(_))) { return; }
        std::thread::sleep(Duration::from_millis(50));
    }
    let _=child.kill(); let _=child.wait();
}
fn run()->Result<(),Box<dyn std::error::Error>> {
    let exe=std::env::current_exe()?;
    let home=exe.parent().unwrap();
    let args:Vec<String>=std::env::args().skip(1).collect();
    let descriptor=if args.first().is_some_and(|s| !s.starts_with("--")) {PathBuf::from(&args[0])} else {home.join("workshop.course.json")};
    let service=home.join("Syntaxia Service.exe");
    if let Some(i)=args.iter().position(|s|s=="--check-report") {
        let status=Command::new(&service).args(["--course",descriptor.to_str().ok_or("Invalid path")?,"--check-report",args.get(i+1).ok_or("Missing report path")?]).creation_flags(0x08000000).status()?;
        if !status.success() {return Err("Course validation failed".into());} return Ok(());
    }
    let mut child=Command::new(&service).arg("--course").arg(&descriptor)
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).creation_flags(0x08000000).spawn()?;
    let stdout=child.stdout.take().ok_or("Could not read service status")?;
    let (ready_tx,ready_rx)=std::sync::mpsc::channel();
    let (ack_tx,ack_rx)=std::sync::mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Ok(v)=serde_json::from_str::<Value>(&line) {
                if v["kind"]=="ready" || v["kind"]=="error" { let _=ready_tx.send(v); }
                else { let _=ack_tx.send(v); }
            }
        }
    });
    let ready=match ready_rx.recv_timeout(Duration::from_secs(30)) {
        Ok(v)=>v,Err(e)=>{let _=child.kill(); return Err(format!("The local lesson service did not start: {e}").into());}
    };
    if ready["kind"]=="error" {return Err(ready["message"].as_str().unwrap_or("Course could not open").into());}
    let port=ready["port"].as_u64().ok_or("Invalid service port")?;
    let base=format!("http://127.0.0.1:{port}");
    let mut url:tauri::Url=format!("{base}/").parse()?;
    url.query_pairs_mut().append_pair("desktop","1").append_pair("mission",ready["mission"].as_str().unwrap_or(""));
    let runtime=Arc::new(Runtime{child:Mutex::new(child),ack:Mutex::new(None),changed:Condvar::new(),leaving:AtomicBool::new(false),allowed:AtomicBool::new(false),sequence:AtomicU64::new(1),catalog:PathBuf::from(ready["catalog"].as_str().ok_or("Invalid catalog")?),database:PathBuf::from(ready["database"].as_str().ok_or("Invalid database")?)});
    let reader=runtime.clone();
    std::thread::spawn(move || { for ack in ack_rx { *reader.ack.lock().unwrap()=Some(ack);reader.changed.notify_all(); } });
    let setup_runtime=runtime.clone();
    let app=tauri::Builder::default().setup(move |app| {
        use tauri::menu::{Menu,MenuItem,Submenu,PredefinedMenuItem};
        let menu=Submenu::with_items(app,"Course",true,&[
            &MenuItem::with_id(app,"reload","Reload lessons",true,None::<&str>)?,
            &MenuItem::with_id(app,"open","Open another course...",true,None::<&str>)?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app,"lessons","Open lesson folder",true,None::<&str>)?,
            &MenuItem::with_id(app,"progress","Open progress folder",true,None::<&str>)?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app,"exit","Exit",true,None::<&str>)?,
        ])?;
        let allowed_origin=base.clone();
        let window=WebviewWindowBuilder::new(app,"main",WebviewUrl::External(url))
            .title("Syntaxia").inner_size(1440.0,940.0).min_inner_size(900.0,650.0)
            .theme(Some(tauri::Theme::Dark)).disable_drag_drop_handler()
            .background_color(tauri::webview::Color(24,22,29,255))
            .icon(tauri::image::Image::from_bytes(include_bytes!("../../assets/workshop-taskbar.png"))?)?
            .on_navigation(move |url|url.origin().ascii_serialization()==allowed_origin)
            .on_download(|_,event| {
                if let tauri::webview::DownloadEvent::Requested{destination,..}=event {
                    let name=destination.file_name().and_then(|s|s.to_str()).unwrap_or("workshop-download");
                    if let Some(path)=rfd::FileDialog::new().set_file_name(name).save_file() {*destination=path;} else {return false;}
                } true
            }).build()?;
        window.set_menu(Menu::with_items(app,&[&menu])?)?;
        let handler_window=window.clone();let handler_runtime=setup_runtime.clone();
        window.on_window_event(move |event|if let WindowEvent::CloseRequested{api,..}=event {
            if !handler_runtime.allowed.load(Ordering::SeqCst) {api.prevent_close();leave(handler_window.clone(),handler_runtime.clone(),true);}
        });
        let menu_runtime=setup_runtime.clone();
        app.on_menu_event(move |app,event| {
            let Some(window)=app.get_webview_window("main") else {return;};
            match event.id().as_ref() {
                "reload"=>leave(window,menu_runtime.clone(),false),
                "exit"=>{let _=window.close();},
                "lessons"|"progress"=>{
                    let file=if event.id().as_ref()=="lessons" {&menu_runtime.catalog} else {&menu_runtime.database};
                    if let Some(parent)=file.parent() {let _=Command::new("explorer.exe").arg(parent).spawn();}
                },
                "open"=>{if let Some(path)=rfd::FileDialog::new().add_filter("Workshop course",&["json"]).pick_file() {if let Ok(exe)=std::env::current_exe() {let _=Command::new(exe).arg(path).creation_flags(0x08000000).spawn();}}},
                _=>()
            }
        });
        Ok(())
    }).build(tauri::generate_context!())?;
    let cleanup=runtime.clone();
    app.run(move |_,event|if matches!(event,RunEvent::Exit) {stop(&cleanup);});
    // A failed setup also drops stdin when this function returns.
    Ok(())
}
fn main(){if let Err(e)=run(){tell(&format!("Syntaxia could not open.\n\n{e}"));}}

