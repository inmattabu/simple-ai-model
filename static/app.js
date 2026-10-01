const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message');

const addMessage = (text, role) => {
  const box = document.createElement('div');
  box.className = `message ${role}`;
  box.textContent = text;
  chatWindow.appendChild(box);
  chatWindow.scrollTop = chatWindow.scrollHeight;
};

const sendMessage = async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }

  addMessage(text, 'user');
  messageInput.value = '';

  const history = Array.from(chatWindow.querySelectorAll('.message')).map((el) => {
    const role = el.classList.contains('user') ? 'user' : 'assistant';
    return { role, content: el.textContent };
  });

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: text,
        history: history.slice(0, -1),
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Something went wrong');
    }

    addMessage(data.reply, 'bot');
  } catch (error) {
    addMessage(error.message || 'Failed to get a response.', 'bot');
  }
};

chatForm.addEventListener('submit', sendMessage);
addMessage('Hello! Ask me anything.', 'bot');
