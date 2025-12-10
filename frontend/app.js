const api = (path) => `${window.location.origin}${path}`;

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

function renderList(items = [], label) {
  if (!items?.length) return "";
  return `<div class="block"><h4>${label}</h4>${items
    .map((i) => `<div class="pill">${i}</div>`)
    .join("")}</div>`;
}

function renderAnalysis(analysis) {
  if (!analysis) return "Нет данных";

  const blocks = [];

  // Общий итог (summary)
  if (analysis.summary) {
    blocks.push(`<div class="block"><h4>Итог</h4>${analysis.summary}</div>`);
  }

  // Текстовый блоки (без рекомендаций, чтобы сохранить порядок для изображений/парсинга)
  if (analysis.strengths || analysis.weaknesses || analysis.unique_offers) {
    blocks.push(renderList(analysis.strengths, "Сильные стороны"));
    blocks.push(renderList(analysis.weaknesses, "Слабые стороны"));
    blocks.push(renderList(analysis.unique_offers, "Уникальные предложения"));
  }

  // Для изображений/парсинга: порядок строго
  // 1) Описание
  if (analysis.description) {
    blocks.push(`<div class="block"><h4>Описание</h4>${analysis.description}</div>`);
  }

  // 2) Стиль (visual_style_score, иначе design_score)
  const styleScore =
    analysis.visual_style_score !== null && analysis.visual_style_score !== undefined
      ? analysis.visual_style_score
      : analysis.design_score;
  if (styleScore !== null && styleScore !== undefined) {
    blocks.push(
      `<div class="block"><h4>Стиль</h4>Оценка: ${styleScore}/10</div>`
    );
  }

  // 3) Разбор стиля
  if (analysis.visual_style_analysis) {
    blocks.push(`<div class="block"><h4>Разбор стиля</h4>${analysis.visual_style_analysis}</div>`);
  }

  // 4) Маркетинговые инсайты
  if (analysis.marketing_insights) {
    blocks.push(renderList(analysis.marketing_insights, "Маркетинговые инсайты"));
  }

  // 5) Рекомендации (общие)
  if (analysis.recommendations) {
    blocks.push(renderList(analysis.recommendations, "Рекомендации"));
  }

  // Дополнительно: анимации (если есть)
  if (analysis.animation_potential) {
    blocks.push(`<div class="block"><h4>Анимации</h4>${analysis.animation_potential}</div>`);
  }

  return blocks.filter(Boolean).join("");
}

function renderError(err) {
  return `<div class="block"><h4>Ошибка</h4>${err}</div>`;
}

document.getElementById("analyze-text-btn").onclick = async () => {
  const text = document.getElementById("text-input").value.trim();
  if (!text) return alert("Введите текст");
  const el = document.getElementById("text-result");
  el.textContent = "Загрузка...";
  const data = await postJSON(api("/analyze_text"), { text });
  if (!data.success) {
    el.innerHTML = renderError(data.error || "Неизвестная ошибка");
    return;
  }
  el.innerHTML = renderAnalysis(data.analysis);
};

document.getElementById("analyze-image-btn").onclick = async () => {
  const file = document.getElementById("image-input").files[0];
  if (!file) return alert("Выберите файл");
  const el = document.getElementById("image-result");
  el.textContent = "Загрузка...";
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(api("/analyze_image"), { method: "POST", body: form });
  const data = await res.json();
  if (!data.success) {
    el.innerHTML = renderError(data.error || "Неизвестная ошибка");
    return;
  }
  el.innerHTML = renderAnalysis(data.analysis);
};

document.getElementById("parse-btn").onclick = async () => {
  const url = document.getElementById("url-input").value.trim();
  if (!url) return alert("Введите URL");
  const el = document.getElementById("parse-result");
  el.textContent = "Загрузка...";
  const data = await postJSON(api("/parse_demo"), { url });
  if (!data.success) {
    el.innerHTML = renderError(data.error || "Неизвестная ошибка");
    return;
  }
  const { analysis } = data.data || {};
  el.innerHTML = renderAnalysis(analysis);
};

async function loadHistory() {
  const el = document.getElementById("history-list");
  const res = await fetch(api("/history"));
  const data = await res.json();
  if (!data.items?.length) {
    el.textContent = "Пока пусто";
    return;
  }
  const iconMap = {
    text: "📝",
    image: "🖼️",
    parse: "🌐",
  };
  const titleMap = {
    text: "Анализ текста",
    image: "Анализ изображения",
    parse: "Парсинг сайта",
  };
  el.innerHTML = data.items
    .map((i) => {
      const icon = iconMap[i.request_type] || "📄";
      const title = titleMap[i.request_type] || i.request_type;
      return `<div class="history-item">
        <div class="history-icon">${icon}</div>
        <div class="history-body">
          <div class="history-title">${title}</div>
          <div class="history-summary">${i.request_summary}</div>
          <div class="muted">${i.response_summary}</div>
        </div>
      </div>`;
    })
    .join("");
}
document.getElementById("history-refresh").onclick = loadHistory;

document.getElementById("history-clear").onclick = async () => {
  await fetch(api("/history"), { method: "DELETE" });
  loadHistory();
};

// Навигация по секциям
document.querySelectorAll(".menu-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".menu-item").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const id = btn.dataset.target;
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  });
});

loadHistory();

