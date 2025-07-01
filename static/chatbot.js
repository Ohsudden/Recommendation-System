document.getElementById('open-chatbot').onclick = function () {
    var win = document.getElementById('chatbot-window');
    win.style.display = win.style.display === 'none' ? 'flex' : 'none';
};

document.getElementById('chatbot-form').onsubmit = async function (e) {
    e.preventDefault();
    const input = document.getElementById('chatbot-input');
    const msg = input.value.trim();
    if (!msg) return;
    const messagesDiv = document.getElementById('chatbot-messages');
    messagesDiv.innerHTML += `
  <div class="chatbot-message chatbot-message-user">
    <img class="chatbot-avatar" src="/static/user_avatar.png" alt="You">
    <div class="chatbot-bubble">
      <div class="chatbot-nickname chatbot-nickname-user">You</div>
      ${msg}
    </div>
  </div>`;
    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    try {
        const resp = await fetch('/chat-api', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg})
        });
        const data = await resp.json();
        messagesDiv.innerHTML += `
  <div class="chatbot-message chatbot-message-bot">
    <img class="chatbot-avatar" src="/static/bot_avatar.png" alt="Bot">
    <div class="chatbot-bubble">
      <div class="chatbot-nickname">Bot</div>
      ${data.response || data.error}
    </div>
  </div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (err) {
        messagesDiv.innerHTML += `
      <div class="chatbot-message chatbot-message-bot">
        <img class="chatbot-avatar" src="/static/bot_avatar.png" alt="Bot">
        <div class="chatbot-bubble"><b>Bot:</b> Sorry, there was a problem connecting to the assistant.</div>
      </div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
};