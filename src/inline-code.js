// Lesson authors explicitly mark syntax with backticks. Everything else is
// inserted as text, so ordinary prose and untrusted course text stay literal.
export function appendInlineCode(node, text) {
  let offset = 0;
  for (const match of text.matchAll(/`([^`\r\n]+)`/g)) {
    node.append(text.slice(offset, match.index));
    const code = document.createElement('code');
    code.className = 'inline-code';
    code.textContent = match[1];
    node.append(code);
    offset = match.index + match[0].length;
  }
  node.append(text.slice(offset));
  return node;
}
