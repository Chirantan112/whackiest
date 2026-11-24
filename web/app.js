/**
 * TASKORA - Frontend Application Logic
 * Vanilla JavaScript implementation for Speech Recognition, TTS with ElevenLabs + fallback,
 * natural language extraction, local job search, job posting, and reporting.
 */

// Global State
const state = {
  language: "en", // "en", "hi", or "kn"
  recognition: null,
  isListening: false,
  areas: [],
  skills: [],
  currentMatches: []
};

// UI Translations
const TRANSLATIONS = {
  en: {
    tagline: "Say your skill. Find work nearby.",
    micIdle: "Tap microphone to speak",
    micListening: "Listening... speak now",
    micError: "Speech recognition error. Please type below.",
    micNotSupported: "Speech recognition not supported in this browser. Please type.",
    searchBtn: "Find Nearby Jobs",
    callBtn: "Call Employer",
    listenBtn: "Read Aloud",
    reportBtn: "Report Job",
    postJobBtn: "Confirm & Post Job",
    extractBtn: "Extract Details",
    demoDisclaimer: "Demo data. Employer verification is not implemented yet.",
    micPermission: "Allow microphone access in your browser, then try again.",
    micNetwork: "Speech service is unavailable. Check your internet connection.",
    micBusy: "Microphone is already active. Please wait a moment.",
    micGeneric: "Could not start the microphone. Please type your request."
  },
  hi: {
    tagline: "अपना हुनर बोलें। पास में काम पाएं।",
    micIdle: "बोलने के लिए माइक दबाएं",
    micListening: "सुन रहे हैं... अब बोलें",
    micError: "आवाज पहचानने में समस्या हुई। कृपया नीचे लिखें।",
    micNotSupported: "इस ब्राउज़र में आवाज की सुविधा उपलब्ध नहीं है। कृपया लिखें।",
    searchBtn: "आस-पास काम खोजें",
    callBtn: "नियोक्ता को कॉल करें",
    listenBtn: "सुनें (बोलकर बताएं)",
    reportBtn: "गलत काम की शिकायत करें",
    postJobBtn: "पुष्टि करें और काम पोस्ट करें",
    extractBtn: "विवरण निकालें",
    demoDisclaimer: "डेमो डेटा। नियोक्ता सत्यापन अभी लागू नहीं किया गया है।",
    micPermission: "ब्राउज़र में माइक्रोफ़ोन की अनुमति दें और फिर कोशिश करें।",
    micNetwork: "आवाज़ सेवा उपलब्ध नहीं है। इंटरनेट कनेक्शन जाँचें।",
    micBusy: "माइक्रोफ़ोन पहले से सक्रिय है। कृपया प्रतीक्षा करें।",
    micGeneric: "माइक्रोफ़ोन शुरू नहीं हो सका। कृपया लिखें।"
  },
  kn: {
    tagline: "ನಿಮ್ಮ ಕೌಶಲ್ಯ ಹೇಳಿ. ಹತ್ತಿರದಲ್ಲೇ ಕೆಲಸ ಹುಡುಕಿ.",
    micIdle: "ಮಾತನಾಡಲು ಮೈಕ್ ಒತ್ತಿ",
    micListening: "ಕೇಳುತ್ತಿದ್ದೇವೆ... ಈಗ ಮಾತನಾಡಿ",
    micError: "ಮಾತನ್ನು ಗುರುತಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಕೆಳಗೆ ಟೈಪ್ ಮಾಡಿ.",
    micNotSupported: "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಟೈಪ್ ಮಾಡಿ.",
    searchBtn: "ಹತ್ತಿರದ ಕೆಲಸ ಹುಡುಕಿ",
    callBtn: "ಉದ್ಯೋಗದಾತರಿಗೆ ಕರೆ ಮಾಡಿ",
    listenBtn: "ಧ್ವನಿಯಾಗಿ ಕೇಳಿ",
    reportBtn: "ಕೆಲಸವನ್ನು ವರದಿ ಮಾಡಿ",
    postJobBtn: "ಖಚಿತಪಡಿಸಿ ಮತ್ತು ಕೆಲಸ ಪ್ರಕಟಿಸಿ",
    extractBtn: "ವಿವರಗಳನ್ನು ಪಡೆಯಿರಿ",
    demoDisclaimer: "ಡೆಮೊ ಮಾಹಿತಿ. ಉದ್ಯೋಗದಾತರ ಪರಿಶೀಲನೆ ಇನ್ನೂ ಜಾರಿಯಾಗಿಲ್ಲ.",
    micPermission: "ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಮೈಕ್ರೊಫೋನ್ ಅನುಮತಿಸಿ, ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    micNetwork: "ಧ್ವನಿ ಸೇವೆ ಲಭ್ಯವಿಲ್ಲ. ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ.",
    micBusy: "ಮೈಕ್ರೊಫೋನ್ ಈಗಾಗಲೇ ಸಕ್ರಿಯವಾಗಿದೆ. ಸ್ವಲ್ಪ ಕಾಯಿರಿ.",
    micGeneric: "ಮೈಕ್ರೊಫೋನ್ ಪ್ರಾರಂಭಿಸಲಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಟೈಪ್ ಮಾಡಿ."
  }
};

// Initialize Speech Recognition
function initSpeechRecognition(transcriptCallback, statusCallback) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (statusCallback) statusCallback(TRANSLATIONS[state.language].micNotSupported);
    return null;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = getSpeechLocale(state.language);

  state.recognition = recognition;

  recognition.onstart = () => {
    state.isListening = true;
    if (statusCallback) statusCallback(TRANSLATIONS[state.language].micListening, true);
  };

  recognition.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript;
    }
    if (transcriptCallback) transcriptCallback(transcript);
  };

  recognition.onerror = (event) => {
    state.isListening = false;
    const key = event.error === "not-allowed" || event.error === "service-not-allowed" ? "micPermission" : event.error === "network" ? "micNetwork" : event.error === "audio-capture" ? "micPermission" : "micError";
    if (statusCallback) statusCallback(TRANSLATIONS[state.language][key] || TRANSLATIONS[state.language].micError, false);
  };

  recognition.onend = () => {
    state.isListening = false;
    if (statusCallback) statusCallback(TRANSLATIONS[state.language].micIdle, false);
  };

  return recognition;
}

// Language Switcher
function setLanguage(lang) {
  state.language = lang;
  document.documentElement.lang = lang;
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });

  const texts = TRANSLATIONS[lang];
  document.querySelectorAll("[data-i18n]").forEach(elem => {
    const key = elem.getAttribute("data-i18n");
    if (texts[key]) {
      elem.textContent = texts[key];
    }
  });

  if (state.recognition) {
    try {
      state.recognition.lang = getSpeechLocale(lang);
    } catch (error) {
      console.warn("Could not update speech language", error);
    }
  }
}

// Text to Speech (TTS)
async function speakText(text, customLang) {
  const lang = customLang || state.language;
  if (!text) return;

  try {
    // Try ElevenLabs backend endpoint
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: lang })
    });

    const data = await response.json();

    if (data.success && data.audio_url) {
      const audio = new Audio(data.audio_url);
      audio.play();
      return;
    }
  } catch (err) {
    console.warn("Backend TTS request failed, falling back to browser synthesis", err);
  }

  // Graceful Fallback: Browser Web SpeechSynthesis
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = getSpeechLocale(lang);
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  } else {
    showToast("Text-to-speech is not supported in this browser.");
  }
}

// Toast Notification
function showToast(message) {
  let toast = document.getElementById("toastNotification");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toastNotification";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3500);
}

// Fetch Metadata (Areas & Skills)
async function loadMetadata() {
  try {
    const [areasRes, skillsRes] = await Promise.all([
      fetch("/api/areas"),
      fetch("/api/skills")
    ]);
    const areasData = await areasRes.json();
    const skillsData = await skillsRes.json();
    state.areas = areasData.areas || [];
    state.skills = skillsData.skills || [];
  } catch (e) {
    console.error("Failed to load metadata", e);
  }
}

// Natural Language Parser Call
async function parseText(text) {
  const res = await fetch("/api/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  return await res.json();
}

// Search Jobs API Call
async function fetchMatchingJobs(skill, area, maxRadiusKm = 15.0) {
  const url = `/api/jobs/search?skill=${encodeURIComponent(skill)}&area=${encodeURIComponent(area)}&max_radius_km=${maxRadiusKm}`;
  const res = await fetch(url);
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || "Job search failed");
  }
  return await res.json();
}

// Report Job API Call
async function reportJobById(jobId) {
  const res = await fetch(`/api/jobs/${jobId}/report`, { method: "POST" });
  if (!res.ok) {
    throw new Error("Failed to report job");
  }
  return await res.json();
}

// Export for page scripts
window.TASKORA = {
  state,
  TRANSLATIONS,
  initSpeechRecognition,
  setLanguage,
  speakText,
  showToast,
  loadMetadata,
  parseText,
  fetchMatchingJobs,
  reportJobById
};
