/* ==========================================================================
   PersonalityRF — app.js
   Lenis smooth scroll + GSAP/ScrollTrigger animations + Chart.js visualizations
   ========================================================================== */

(function () {
  "use strict";

  const META = window.__META__;

  /* -----------------------------------------------------------------------
     1. Lenis Smooth Scroll + GSAP sync
     ----------------------------------------------------------------------- */
  const lenis = new Lenis({
    duration: 1.1,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
  });

  lenis.on("scroll", ScrollTrigger.update);

  gsap.ticker.add((time) => {
    lenis.raf(time * 1000);
  });
  gsap.ticker.lagSmoothing(0);

  /* -----------------------------------------------------------------------
     2. Split titles into words
     ----------------------------------------------------------------------- */
  function splitWords(el) {
    const text = el.textContent.trim();
    const words = text.split(/\s+/);
    el.innerHTML = words
      .map(
        (w) =>
          `<span class="word-wrap"><span class="word">${w}</span></span>`
      )
      .join(" ");
  }

  document.querySelectorAll("[data-split]").forEach(splitWords);

  /* -----------------------------------------------------------------------
     3. GSAP ScrollTrigger animations
     ----------------------------------------------------------------------- */
  gsap.registerPlugin(ScrollTrigger);

  // 3a. Title word reveals
  document.querySelectorAll("[data-split]").forEach((title) => {
    const words = title.querySelectorAll(".word");
    gsap.from(words, {
      yPercent: 110,
      opacity: 0,
      duration: 0.7,
      ease: "power3.out",
      stagger: 0.06,
      scrollTrigger: {
        trigger: title,
        start: "top 85%",
        toggleActions: "play none none none",
      },
    });
  });

  // 3b. Card entrance animations
  function animateCards() {
    gsap.utils.toArray(".anim-card").forEach((card) => {
      gsap.to(card, {
        opacity: 1,
        y: 0,
        duration: 0.65,
        ease: "power2.out",
        scrollTrigger: {
          trigger: card,
          start: "top 88%",
          toggleActions: "play none none none",
        },
      });
    });
  }
  animateCards();

  // 3c. Metric value count-up
  document.querySelectorAll(".metric-value").forEach((el) => {
    const val = parseFloat(el.textContent);
    if (isNaN(val)) return;
    const obj = { v: 0 };
    gsap.to(obj, {
      v: val,
      duration: 1.4,
      ease: "power2.out",
      scrollTrigger: {
        trigger: el,
        start: "top 90%",
        toggleActions: "play none none none",
      },
      onUpdate: () => {
        el.textContent = obj.v.toFixed(1) + "%";
      },
    });
  });

  /* -----------------------------------------------------------------------
     4. Range slider live value
     ----------------------------------------------------------------------- */
  document.querySelectorAll('input[type="range"]').forEach((slider) => {
    const output = slider
      .closest(".range-wrap")
      .querySelector(".range-val");
    slider.addEventListener("input", () => {
      output.textContent = slider.value;
    });
  });

  /* -----------------------------------------------------------------------
     5. Preset profiles
     ----------------------------------------------------------------------- */
  const PRESETS = {
    extrovert: {
      Time_spent_Alone: 1,
      Social_event_attendance: 8,
      Going_outside: 6,
      Friends_circle_size: 13,
      Post_frequency: 8,
      Stage_fear: "No",
      Drained_after_socializing: "No",
    },
    introvert: {
      Time_spent_Alone: 9,
      Social_event_attendance: 1,
      Going_outside: 1,
      Friends_circle_size: 2,
      Post_frequency: 1,
      Stage_fear: "Yes",
      Drained_after_socializing: "Yes",
    },
    balanced: {
      Time_spent_Alone: 5,
      Social_event_attendance: 5,
      Going_outside: 3,
      Friends_circle_size: 7,
      Post_frequency: 5,
      Stage_fear: "No",
      Drained_after_socializing: "Yes",
    },
  };

  document.querySelectorAll(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.preset;
      const preset = PRESETS[key];
      if (!preset) return;

      // Highlight active preset
      document
        .querySelectorAll(".preset-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Fill form
      for (const [name, val] of Object.entries(preset)) {
        const el = document.querySelector(`[name="${name}"]`);
        if (!el) continue;
        if (el.type === "range") {
          el.value = val;
          const output = el
            .closest(".range-wrap")
            .querySelector(".range-val");
          if (output) output.textContent = val;
        } else if (el.type === "radio") {
          document
            .querySelectorAll(`[name="${name}"]`)
            .forEach((r) => (r.checked = r.value === val));
        }
      }
    });
  });

  /* -----------------------------------------------------------------------
     6. Form submission & prediction
     ----------------------------------------------------------------------- */
  const form = document.getElementById("predict-form");
  const btnPredict = document.getElementById("btn-predict");
  const resultPlaceholder = document.getElementById("result-placeholder");
  const resultPanel = document.getElementById("result-panel");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Gather data
    const formData = new FormData(form);
    const payload = {};
    for (const [k, v] of formData.entries()) {
      payload[k] = v;
    }

    // Show loader
    btnPredict.querySelector(".btn-text").textContent = "Memproses…";
    btnPredict.querySelector(".btn-loader").hidden = false;
    btnPredict.disabled = true;

    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Terjadi kesalahan.");
        return;
      }

      showResults(data, payload);
    } catch (err) {
      alert("Gagal menghubungi server: " + err.message);
    } finally {
      btnPredict.querySelector(".btn-text").textContent =
        "Prediksi Kepribadian";
      btnPredict.querySelector(".btn-loader").hidden = true;
      btnPredict.disabled = false;
    }
  });

  // Reset form
  form.addEventListener("reset", () => {
    setTimeout(() => {
      document
        .querySelectorAll(".preset-btn")
        .forEach((b) => b.classList.remove("active"));
      document.querySelectorAll('input[type="range"]').forEach((s) => {
        const output = s.closest(".range-wrap").querySelector(".range-val");
        if (output) output.textContent = s.value;
      });
    }, 10);
  });

  /* -----------------------------------------------------------------------
     7. Display results
     ----------------------------------------------------------------------- */
  let comparisonChart = null;
  let importanceChart = null;
  let historyChart = null;
  let lastComparisonData = null;
  let lastHistoryData = null;

  function showResults(data, inputPayload) {
    resultPlaceholder.hidden = true;
    resultPanel.hidden = false;

    const isExtro = data.prediction === "Extrovert";

    // Dynamic theme change based on prediction
    if (isExtro) {
      document.body.classList.remove("theme-introvert");
      document.body.classList.add("theme-extrovert");
    } else {
      document.body.classList.remove("theme-extrovert");
      document.body.classList.add("theme-introvert");
    }

    // Prediction label
    const predLabel = document.getElementById("pred-label");
    predLabel.textContent = isExtro ? "🌟 Extrovert" : "📚 Introvert";
    predLabel.className = "pred-label " + (isExtro ? "extrovert" : "introvert");

    // Probability bars
    const pIntro = data.probability.Introvert || 0;
    const pExtro = data.probability.Extrovert || 0;
    document.getElementById("proba-intro-bar").style.width = pIntro + "%";
    document.getElementById("proba-extro-bar").style.width = pExtro + "%";
    document.getElementById("proba-intro-txt").textContent =
      "Introvert: " + pIntro.toFixed(1) + "%";
    document.getElementById("proba-extro-txt").textContent =
      "Extrovert: " + pExtro.toFixed(1) + "%";

    // Dominant factors
    const factorsList = document.getElementById("factors-list");
    factorsList.innerHTML = "";
    (data.dominant_factors || []).forEach((f) => {
      const li = document.createElement("li");
      li.className = "factor-item";
      li.innerHTML = `
        <span class="factor-dot ${f.closer_to.toLowerCase()}"></span>
        <span class="factor-label">${f.label}</span>
        <span class="factor-value">${f.value} → ${f.closer_to}</span>
      `;
      factorsList.appendChild(li);
    });

    // Comparison chart
    lastComparisonData = data.comparison;
    renderComparisonChart(data.comparison);

    // Refresh other charts to adapt to new theme colors
    renderImportanceChart();

    // Animate result panel
    gsap.fromTo(
      "#pred-card",
      { opacity: 0, scale: 0.95 },
      { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.4)" }
    );
    resultPanel.querySelectorAll(".anim-card").forEach((c) => {
      c.style.opacity = "1";
      c.style.transform = "translateY(0)";
    });

    // Scroll to results
    lenis.scrollTo("#results", { offset: -80 });

    // Update history
    lastHistoryData = data.history;
    updateHistory(data.history);
  }

  /* -----------------------------------------------------------------------
     8. Comparison Chart (Radar)
     ----------------------------------------------------------------------- */
  const RADAR_LABELS = {
    Time_spent_Alone: ["Waktu", "Menyendiri"],
    Social_event_attendance: ["Kehadiran", "Acara Sosial"],
    Going_outside: ["Frekuensi", "Keluar Rumah"],
    Friends_circle_size: ["Jumlah Teman", "Dekat"],
    Post_frequency: ["Frekuensi", "Unggahan Sosmed"]
  };

  function renderComparisonChart(comparison) {
    if (!comparison) return;
    const isLight = document.body.classList.contains("theme-extrovert");

    const labels = [];
    const userData = [];
    const introData = [];
    const extroData = [];

    META.numCols.forEach((col) => {
      const c = comparison[col];
      if (!c) return;
      labels.push(RADAR_LABELS[col] || c.label.split("(")[0].trim());
      userData.push(c.user);
      introData.push(c.mean_introvert);
      extroData.push(c.mean_extrovert);
    });

    const ctx = document.getElementById("chart-comparison").getContext("2d");
    if (comparisonChart) comparisonChart.destroy();

    comparisonChart = new Chart(ctx, {
      type: "radar",
      data: {
        labels,
        datasets: [
          {
            label: "Anda",
            data: userData,
            borderColor: isLight ? "#7c3aed" : "#a78bfa",
            backgroundColor: isLight ? "rgba(124, 58, 237, 0.15)" : "rgba(167, 139, 250, 0.18)",
            borderWidth: 2.5,
            pointRadius: 4,
            pointBackgroundColor: isLight ? "#7c3aed" : "#a78bfa",
          },
          {
            label: "Rata-rata Introvert",
            data: introData,
            borderColor: "#3b82f6",
            backgroundColor: isLight ? "rgba(59, 130, 246, 0.08)" : "rgba(91, 143, 249, 0.08)",
            borderWidth: 2,
            borderDash: [6, 3],
            pointRadius: 3,
            pointBackgroundColor: "#3b82f6",
          },
          {
            label: "Rata-rata Extrovert",
            data: extroData,
            borderColor: isLight ? "#d97706" : "#F6BD16",
            backgroundColor: isLight ? "rgba(217, 119, 6, 0.08)" : "rgba(246, 189, 22, 0.08)",
            borderWidth: 2,
            borderDash: [6, 3],
            pointRadius: 3,
            pointBackgroundColor: isLight ? "#d97706" : "#F6BD16",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: {
            top: 15,
            right: 25,
            bottom: 20,
            left: 25,
          },
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: isLight ? "#334155" : "#9898a4",
              padding: 16,
              font: { size: 12, weight: "500" },
            },
          },
        },
        scales: {
          r: {
            beginAtZero: true,
            grid: { color: isLight ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.07)" },
            angleLines: { color: isLight ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.07)" },
            pointLabels: {
              color: isLight ? "#0f172a" : "#cbd5e1",
              font: { size: 12, weight: "600", family: "Inter, sans-serif" },
              padding: 12,
            },
            ticks: { display: false },
          },
        },
      },
    });
  }

  /* -----------------------------------------------------------------------
     9. Feature Importance Chart (horizontal bar)
     ----------------------------------------------------------------------- */
  function renderImportanceChart() {
    const isLight = document.body.classList.contains("theme-extrovert");
    const items = META.featureImportance;
    const labels = items.map((i) => i.label).reverse();
    const values = items.map((i) => i.importance).reverse();

    const ctx = document.getElementById("chart-importance").getContext("2d");
    if (importanceChart) importanceChart.destroy();

    importanceChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Importance",
            data: values,
            backgroundColor: values.map((v, i) =>
              isLight
                ? `rgba(217, 119, 6, ${0.35 + (i / values.length) * 0.6})`
                : `rgba(108, 99, 255, ${0.35 + (i / values.length) * 0.6})`
            ),
            borderColor: isLight ? "rgba(217, 119, 6, 0.9)" : "rgba(108, 99, 255, 0.8)",
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => (ctx.raw * 100).toFixed(2) + "%",
            },
          },
        },
        scales: {
          x: {
            grid: { color: isLight ? "rgba(0,0,0,0.06)" : "rgba(255,255,255,0.05)" },
            ticks: {
              color: isLight ? "#64748b" : "#6a6a78",
              callback: (v) => (v * 100).toFixed(0) + "%",
            },
          },
          y: {
            grid: { display: false },
            ticks: {
              color: isLight ? "#334155" : "#9898a4",
              font: { size: 11, weight: "500" },
            },
          },
        },
      },
    });
  }

  // Initial render of importance chart
  renderImportanceChart();

  /* -----------------------------------------------------------------------
     10. Session History
     ----------------------------------------------------------------------- */
  const historyEmpty = document.getElementById("history-empty");
  const historyContent = document.getElementById("history-content");

  function updateHistory(history) {
    if (!history || history.length === 0) {
      historyEmpty.hidden = false;
      historyContent.hidden = true;
      return;
    }

    historyEmpty.hidden = true;
    historyContent.hidden = false;

    const isLight = document.body.classList.contains("theme-extrovert");

    // Table
    const tbody = document
      .getElementById("history-table")
      .querySelector("tbody");
    tbody.innerHTML = "";
    history.forEach((h) => {
      const tr = document.createElement("tr");
      const color =
        h.prediction === "Extrovert"
          ? (isLight ? "#d97706" : "var(--extrovert)")
          : (isLight ? "#2563eb" : "var(--introvert)");
      tr.innerHTML = `
        <td>${h.id}</td>
        <td style="color:${color};font-weight:700">${h.prediction}</td>
        <td>${h.probability.Introvert.toFixed(1)}%</td>
        <td>${h.probability.Extrovert.toFixed(1)}%</td>
      `;
      tbody.appendChild(tr);
    });

    // Chart
    const ctx = document.getElementById("chart-history").getContext("2d");
    if (historyChart) historyChart.destroy();

    historyChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: history.map((h) => "#" + h.id),
        datasets: [
          {
            label: "P(Introvert)",
            data: history.map((h) => h.probability.Introvert),
            backgroundColor: isLight ? "rgba(37, 99, 235, 0.75)" : "rgba(91,143,249,.7)",
            borderRadius: 4,
          },
          {
            label: "P(Extrovert)",
            data: history.map((h) => h.probability.Extrovert),
            backgroundColor: isLight ? "rgba(217, 119, 6, 0.75)" : "rgba(246,189,22,.7)",
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: isLight ? "#334155" : "#9898a4",
              padding: 16,
              font: { size: 12 },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: isLight ? "#334155" : "#9898a4" },
          },
          y: {
            grid: { color: isLight ? "rgba(0,0,0,0.06)" : "rgba(255,255,255,0.05)" },
            ticks: {
              color: isLight ? "#64748b" : "#6a6a78",
              callback: (v) => v + "%",
            },
            max: 100,
          },
        },
      },
    });

    // Animate new entries
    gsap.fromTo(
      historyContent,
      { opacity: 0.6 },
      { opacity: 1, duration: 0.4 }
    );
  }

  // Clear history button
  document
    .getElementById("btn-clear-history")
    .addEventListener("click", async () => {
      try {
        await fetch("/api/history/clear", { method: "POST" });
        updateHistory([]);
      } catch (e) {
        console.error(e);
      }
    });

  /* -----------------------------------------------------------------------
     11. Navbar scroll behaviour
     ----------------------------------------------------------------------- */
  const navbar = document.getElementById("navbar");
  window.addEventListener("scroll", () => {
    if (window.scrollY > 60) {
      navbar.classList.add("scrolled");
    } else {
      navbar.classList.remove("scrolled");
    }
  });

  /* -----------------------------------------------------------------------
     12. Smooth-scroll anchor links via Lenis
     ----------------------------------------------------------------------- */
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const target = document.querySelector(a.getAttribute("href"));
      if (target) lenis.scrollTo(target, { offset: -70 });
    });
  });
})();
