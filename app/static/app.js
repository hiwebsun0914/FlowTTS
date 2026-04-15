const socketStatusEl = document.getElementById("socketStatus");
const recognitionStatusEl = document.getElementById("recognitionStatus");
const speechStatusEl = document.getElementById("speechStatus");
const interimTranscriptEl = document.getElementById("interimTranscript");
const chatLogEl = document.getElementById("chatLog");
const startVoiceButton = document.getElementById("startVoiceButton");
const stopVoiceButton = document.getElementById("stopVoiceButton");
const clearButton = document.getElementById("clearButton");
const manualInput = document.getElementById("manualInput");
const sendTextButton = document.getElementById("sendTextButton");

const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let socket = null;
let activeAssistantBubble = null;
let activeTurnId = null;
let selectedVoice = null;

function addMessage(role, text) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.textContent = text;
  chatLogEl.appendChild(message);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
  return message;
}

function setSocketStatus(text) {
  socketStatusEl.textContent = text;
}

function setRecognitionStatus(text) {
  recognitionStatusEl.textContent = text;
}

function setSpeechStatus(text) {
  speechStatusEl.textContent = text;
}

function clearAssistantSpeech() {
  window.speechSynthesis.cancel();
  setSpeechStatus("待机");
}

function chooseVoice() {
  const voices = window.speechSynthesis.getVoices();
  selectedVoice =
    voices.find((voice) => voice.lang === "zh-CN") ||
    voices.find((voice) => voice.lang.startsWith("zh")) ||
    voices[0] ||
    null;
}

function speakText(text) {
  if (!text) {
    return;
  }
  if (!selectedVoice) {
    chooseVoice();
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = selectedVoice?.lang || "zh-CN";
  utterance.voice = selectedVoice;
  utterance.rate = 1.08;
  utterance.pitch = 1;
  utterance.onstart = () => setSpeechStatus("播报中");
  utterance.onend = () => setSpeechStatus("待机");
  utterance.onerror = () => setSpeechStatus("播报异常");
  window.speechSynthesis.speak(utterance);
}

function sendSocketMessage(payload) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    addMessage("system", "WebSocket 未连接，暂时无法发送。");
    return;
  }
  socket.send(JSON.stringify(payload));
}

function sendUserText(text) {
  const cleanText = text.trim();
  if (!cleanText) {
    return;
  }
  clearAssistantSpeech();
  activeAssistantBubble = null;
  activeTurnId = null;
  addMessage("user", cleanText);
  sendSocketMessage({ type: "user_text", text: cleanText });
}

function setupSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socketUrl = `${protocol}://${window.location.host}/api/v1/ws/chat`;
  socket = new WebSocket(socketUrl);

  socket.onopen = () => {
    setSocketStatus("已连接");
    addMessage("system", "语音对话通道已建立。");
  };

  socket.onclose = () => {
    setSocketStatus("已断开");
    addMessage("system", "连接已关闭，3 秒后自动重连。");
    setTimeout(setupSocket, 3000);
  };

  socket.onerror = () => {
    setSocketStatus("连接异常");
  };

  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);

    switch (payload.type) {
      case "ready":
        setSocketStatus(`已连接 · ${payload.llm_model}`);
        break;
      case "user_text_received":
        activeTurnId = payload.turn_id;
        activeAssistantBubble = addMessage("assistant", "");
        break;
      case "assistant_delta":
        if (!activeAssistantBubble || activeTurnId !== payload.turn_id) {
          activeTurnId = payload.turn_id;
          activeAssistantBubble = addMessage("assistant", "");
        }
        activeAssistantBubble.textContent += payload.delta;
        chatLogEl.scrollTop = chatLogEl.scrollHeight;
        break;
      case "assistant_sentence":
        if (activeTurnId === payload.turn_id) {
          speakText(payload.text);
        }
        break;
      case "assistant_done":
        activeTurnId = null;
        break;
      case "assistant_cancelled":
        clearAssistantSpeech();
        break;
      case "history_cleared":
        clearAssistantSpeech();
        chatLogEl.innerHTML = "";
        addMessage("system", "上下文已清空。");
        break;
      case "error":
        addMessage("system", payload.message || "发生未知错误。");
        break;
      default:
        break;
    }
  };
}

function setupRecognition() {
  if (!SpeechRecognitionCtor) {
    setRecognitionStatus("当前浏览器不支持");
    addMessage("system", "当前浏览器不支持 SpeechRecognition，请直接用文本输入。");
    startVoiceButton.disabled = true;
    stopVoiceButton.disabled = true;
    return;
  }

  recognition = new SpeechRecognitionCtor();
  recognition.lang = "zh-CN";
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    setRecognitionStatus("录音中");
    startVoiceButton.disabled = true;
    stopVoiceButton.disabled = false;
    interimTranscriptEl.textContent = "正在听你说话…";
  };

  recognition.onresult = (event) => {
    let finalText = "";
    let interimText = "";

    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      if (result.isFinal) {
        finalText += result[0].transcript;
      } else {
        interimText += result[0].transcript;
      }
    }

    interimTranscriptEl.textContent = interimText || finalText || "等待麦克风输入…";
    if (finalText.trim()) {
      sendUserText(finalText);
    }
  };

  recognition.onerror = (event) => {
    setRecognitionStatus(`异常：${event.error}`);
    stopVoiceButton.disabled = true;
    startVoiceButton.disabled = false;
  };

  recognition.onend = () => {
    setRecognitionStatus("未启动");
    stopVoiceButton.disabled = true;
    startVoiceButton.disabled = false;
  };
}

startVoiceButton.addEventListener("click", () => {
  if (!recognition) {
    return;
  }
  clearAssistantSpeech();
  recognition.start();
});

stopVoiceButton.addEventListener("click", () => {
  recognition?.stop();
});

clearButton.addEventListener("click", () => {
  clearAssistantSpeech();
  sendSocketMessage({ type: "clear_history" });
});

sendTextButton.addEventListener("click", () => {
  sendUserText(manualInput.value);
  manualInput.value = "";
});

manualInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    sendUserText(manualInput.value);
    manualInput.value = "";
  }
});

window.speechSynthesis.onvoiceschanged = chooseVoice;
chooseVoice();
setupSocket();
setupRecognition();
