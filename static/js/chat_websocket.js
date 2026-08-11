/**
 * chat_websocket.js
 * Drop this in static/chat/js/ and include it in your chat templates.
 *
 * Usage (direct chat template):
 *   const socket = buildChatSocket('/ws/dm/{{ conversation.id }}/');
 *
 * Usage (group chat template):
 *   const socket = buildChatSocket('/ws/group/{{ group.id }}/');
 */

function buildChatSocket(wsPath) {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket   = new WebSocket(`${protocol}://${window.location.host}${wsPath}`);

  const input    = document.getElementById('message-input');
  const sendBtn  = document.getElementById('send-btn');
  const msgList  = document.getElementById('message-list');

  // ── Send ────────────────────────────────────────────────────────────────────

  function sendMessage() {
    const text = input.value.trim();
    if (!text || socket.readyState !== WebSocket.OPEN) return;

    // The consumer expects exactly this shape:
    socket.send(JSON.stringify({ message: text }));
    input.value = '';
    input.focus();
  }

  sendBtn.addEventListener('click', sendMessage);

  input.addEventListener('keydown', (e) => {
    // Send on Enter; allow Shift+Enter for newlines
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // ── Receive ─────────────────────────────────────────────────────────────────

  socket.addEventListener('message', (e) => {
    const data = JSON.parse(e.data);

    /*
     * BUG FIX (consumer side — already patched in consumers.py):
     * Previously the server forwarded the raw channel-layer event which
     * included `type: "chat_message"`.  That key is now stripped server-side.
     * The payload arriving here is clean:
     *   { message, sender_id, sender_username, sender_avatar, timestamp, message_id }
     */

    const isSelf = String(data.sender_id) === String(CURRENT_USER_ID); // set in template

    const li = document.createElement('li');
    li.className  = isSelf ? 'message message--self' : 'message message--other';
    li.dataset.id = data.message_id;
    li.innerHTML  = `
      <img class="message__avatar" src="${data.sender_avatar}" alt="${data.sender_username}">
      <div class="message__body">
        <span class="message__author">${data.sender_username}</span>
        <p   class="message__text">${escapeHtml(data.message)}</p>
        <time class="message__time">${data.timestamp}</time>
      </div>`;

    msgList.appendChild(li);
    msgList.scrollTop = msgList.scrollHeight;
  });

  // ── Connection state ─────────────────────────────────────────────────────────

  socket.addEventListener('open',  ()  => { sendBtn.disabled = false; });
  socket.addEventListener('close', ()  => { sendBtn.disabled = true;  });
  socket.addEventListener('error', (e) => { console.error('WS error', e); });

  return socket;
}

// Simple XSS guard
function escapeHtml(str) {
  return str
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}
