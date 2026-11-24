/**
 * TASKORA - Frontend Application Logic
 * Vanilla JavaScript implementation for Speech Recognition, TTS with ElevenLabs + fallback,
 * natural language extraction, local job search, job posting, and reporting.
 */

// Global State
const state = {
  language: "en", // "en" or "hi"
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
    demoDisclaimer: "Demo data. Employer verification is not implemented yet."
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
    demoDisclaimer: "डेमो डेटा। नियोक्ता सत्यापन अभी लागू नहीं किया गया है।"
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
  recognition.lang = state.language === "hi" ? "hi-IN" : "en-IN";

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
    if (statusCallback) statusCallback(`${TRANSLATIONS[state.language].micError} (${event.error})`, false);
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
    state.recognition.lang = lang === "hi" ? "hi-IN" : "en-IN";
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
    utterance.lang = lang === "hi" ? "hi-IN" : "en-IN";
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
