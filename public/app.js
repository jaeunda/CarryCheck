/* Shared static asset for local and Vercel runtimes. */
const state = { options: null };

const elements = {
  form: document.querySelector("#baggageForm"),
  airline: document.querySelector("#airline"),
  routeType: document.querySelector("#routeType"),
  originCountry: document.querySelector("#originCountry"),
  destinationCountry: document.querySelector("#destinationCountry"),
  transitCountry: document.querySelector("#transitCountry"),
  itemText: document.querySelector("#itemText"),
  itemType: document.querySelector("#itemType"),
  cccMark: document.querySelector("#cccMark"),
  recalledBattery: document.querySelector("#recalledBattery"),
  exampleList: document.querySelector("#exampleList"),
  datasetBadge: document.querySelector("#datasetBadge"),
  resetButton: document.querySelector("#resetButton"),
  submitButton: document.querySelector("#submitButton"),
  formError: document.querySelector("#formError"),
  emptyState: document.querySelector("#emptyState"),
  loadingState: document.querySelector("#loadingState"),
  resultContent: document.querySelector("#resultContent"),
  resultPanel: document.querySelector("#resultPanel"),
  overallBadge: document.querySelector("#overallBadge"),
  resultContext: document.querySelector("#resultContext"),
  resultHeadline: document.querySelector("#resultHeadline"),
  parsedValues: document.querySelector("#parsedValues"),
  carryCard: document.querySelector("#carryCard"),
  checkedCard: document.querySelector("#checkedCard"),
  carryStatus: document.querySelector("#carryStatus"),
  checkedStatus: document.querySelector("#checkedStatus"),
  aiAnswerBlock: document.querySelector("#aiAnswerBlock"),
  aiAnswerTitle: document.querySelector("#aiAnswerTitle"),
  aiAnswerStatus: document.querySelector("#aiAnswerStatus"),
  aiAnswerText: document.querySelector("#aiAnswerText"),
  aiAnswerMeta: document.querySelector("#aiAnswerMeta"),
  resultSections: document.querySelector("#resultSections"),
  sourceBlock: document.querySelector("#sourceBlock"),
};

const advancedInputs = {
  watt_hours: "#wattHours",
  milliamp_hours: "#milliampHours",
  voltage: "#voltage",
  container_ml: "#containerMl",
  total_ml: "#totalMl",
  weight_kg: "#weightKg",
  count: "#count",
};

const triStateInputs = {
  removable_battery: "#removableBattery",
  physical_disconnect: "#physicalDisconnect",
  heat_safety_mode: "#heatSafetyMode",
  ccc_mark: "#cccMark",
};

const checkInputs = {
  damaged: "#damaged",
  medical_exception: "#medicalException",
  duty_free: "#dutyFree",
  torch_lighter: "#torchLighter",
  recalled_battery: "#recalledBattery",
};

const countryStatusLabels = {
  not_applicable: "해당 없음",
  information: "안내",
  within_allowance: "한도 이내",
  conditional: "조건부",
  review_required: "사전 확인 필요",
  declaration_required: "세관 신고 필요",
  prohibited: "입국 반입 금지",
  allowed: "운송 가능",
  needs_information: "추가 확인 필요",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function addCountryOptions(select) {
  state.options.countries.forEach((country) => {
    select.add(new Option(country.name, country.code));
  });
}

async function loadOptions() {
  try {
    const response = await fetch("/api/options");
    if (!response.ok) throw new Error("설정 정보를 불러오지 못했습니다.");
    state.options = await response.json();

    state.options.airlines.forEach((airline) => {
      elements.airline.add(new Option(airline.name, airline.code));
    });
    state.options.item_types.forEach((item) => {
      elements.itemType.add(new Option(item.label, item.value));
    });
    [elements.originCountry, elements.destinationCountry, elements.transitCountry].forEach(addCountryOptions);
    elements.datasetBadge.textContent = `국가 규정 확인일 ${state.options.dataset.country_verified_date}`;
    renderExamples();
    restorePreferences();
  } catch (error) {
    showError(error.message);
    elements.datasetBadge.textContent = "국가 규정 연결 실패";
  }
}

function renderExamples() {
  elements.exampleList.replaceChildren();
  state.options.examples.forEach((example) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "example-chip";
    button.textContent = example.label;
    button.addEventListener("click", () => {
      elements.airline.value = example.airline;
      elements.routeType.value = example.route_type || "";
      elements.originCountry.value = example.origin_country || "";
      elements.destinationCountry.value = example.destination_country || "";
      elements.transitCountry.value = example.transit_country || "";
      elements.itemText.value = example.item_text;
      elements.itemText.focus();
      savePreferences();
    });
    elements.exampleList.append(button);
  });
}

function buildPayload() {
  const overrides = {};
  if (elements.itemType.value) overrides.item_type = elements.itemType.value;

  Object.entries(advancedInputs).forEach(([key, selector]) => {
    const value = document.querySelector(selector).value;
    if (value !== "") overrides[key] = Number(value);
  });
  Object.entries(triStateInputs).forEach(([key, selector]) => {
    const value = document.querySelector(selector).value;
    if (value !== "") overrides[key] = value === "true";
  });
  Object.entries(checkInputs).forEach(([key, selector]) => {
    if (document.querySelector(selector).checked) overrides[key] = true;
  });

  return {
    airline: elements.airline.value,
    route_type: elements.routeType.value || null,
    origin_country: elements.originCountry.value || null,
    destination_country: elements.destinationCountry.value || null,
    transit_country: elements.transitCountry.value || null,
    item_text: elements.itemText.value.trim(),
    overrides,
  };
}

function setView(view) {
  elements.emptyState.hidden = view !== "empty";
  elements.loadingState.hidden = view !== "loading";
  elements.resultContent.hidden = view !== "result";
}

function showError(message) {
  elements.formError.textContent = message;
  elements.formError.hidden = false;
}

function clearError() {
  elements.formError.hidden = true;
  elements.formError.textContent = "";
}

function statusClass(status) {
  return `status-${status}`;
}

function setStatusElement(element, status) {
  element.classList.remove("status-allowed", "status-conditional", "status-prohibited", "status-needs_information");
  element.classList.add(statusClass(status));
}

function measurementChips(item, countryChecks) {
  const values = [];
  if (item.watt_hours != null) values.push(`${Number(item.watt_hours).toFixed(1)}Wh`);
  if (item.milliamp_hours != null) values.push(`${Number(item.milliamp_hours).toLocaleString()}mAh`);
  if (item.voltage != null) values.push(`${item.voltage}V`);
  if (item.container_ml != null) values.push(`용기 ${item.container_ml}mL`);
  if (item.total_ml != null) values.push(`총 ${item.total_ml}mL`);
  if (item.weight_kg != null) values.push(`${item.weight_kg}kg`);
  if (item.count != null) values.push(`${item.count}개`);
  if (countryChecks.route_type) values.push(countryChecks.route_type === "international" ? "국제선" : "국내선");
  return values;
}

function renderListSection(title, items, extraClass = "") {
  if (!items?.length) return "";
  return `<section class="result-section ${extraClass}"><h3>${escapeHtml(title)}</h3><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>`;
}

function renderCountryRuleSection(title, status, rules) {
  if (!rules?.length) return "";
  const alertStatuses = new Set(["prohibited", "declaration_required", "review_required"]);
  const extraClass = alertStatuses.has(status) ? "missing-section" : "";
  const label = countryStatusLabels[status] || status;
  const items = rules.map((rule) => {
    const conditions = rule.conditions?.length ? `<ul>${rule.conditions.map((condition) => `<li>${escapeHtml(condition)}</li>`).join("")}</ul>` : "";
    return `<li><strong>${escapeHtml(countryStatusLabels[rule.status] || rule.status)}</strong> · ${escapeHtml(rule.message)}${conditions}</li>`;
  }).join("");
  return `<section class="result-section ${extraClass}"><h3>${escapeHtml(title)} · ${escapeHtml(label)}</h3><ul>${items}</ul></section>`;
}

function uniqueSources(decisionSources, countryChecks) {
  const sources = [...(decisionSources || [])];
  [...(countryChecks.aviation_rules || []), ...(countryChecks.entry_rules || [])].forEach((rule) => {
    if (rule.source) sources.push(rule.source);
  });
  return [...new Map(sources.map((source) => [source.rule_id, source])).values()];
}

function routeLabel(countryChecks) {
  const origin = countryChecks.origin_country_name || "출발국 미지정";
  const destination = countryChecks.destination_country_name || "도착국 미지정";
  const transit = countryChecks.transit_country_name ? ` · ${countryChecks.transit_country_name} 경유` : "";
  return `${origin} → ${destination}${transit}`;
}

function renderResult(data) {
  const decision = data.decision;
  const labels = data.status_labels;
  const item = decision.item;
  const countryChecks = data.country_checks || {};

  elements.resultContext.textContent = `${decision.airline_name} · ${item.item_name} · ${routeLabel(countryChecks)}`;
  const journeyStatus = countryChecks.journey_status || decision.overall;
  elements.overallBadge.textContent = labels[journeyStatus] || countryStatusLabels[journeyStatus];
  setStatusElement(elements.overallBadge, journeyStatus);

  const headlines = {
    allowed: "항공 운송 기준상 반입할 수 있어요.",
    conditional: "조건을 지키면 항공 운송이 가능해요.",
    prohibited: "기내와 위탁 모두 반입할 수 없어요.",
    needs_information: "추가 정보를 확인해야 정확히 판정할 수 있어요.",
  };
  elements.resultHeadline.textContent = headlines[decision.overall];
  if (countryChecks.entry_status === "prohibited") {
    elements.resultHeadline.textContent = `${countryChecks.destination_country_name || "도착국"} 입국 시 반입할 수 없는 물품입니다.`;
  } else if (countryChecks.entry_status === "declaration_required") {
    elements.resultHeadline.textContent = "항공 운송과 별도로 도착 세관 신고가 필요합니다.";
  } else if (countryChecks.entry_status === "review_required") {
    elements.resultHeadline.textContent = "도착국 허가·검역 요건을 출발 전에 확인하세요.";
  }
  elements.parsedValues.innerHTML = measurementChips(item, countryChecks).map((value) => `<span>${escapeHtml(value)}</span>`).join("");

  elements.carryStatus.textContent = labels[decision.carry_on.status];
  elements.checkedStatus.textContent = labels[decision.checked.status];
  setStatusElement(elements.carryCard, decision.carry_on.status);
  setStatusElement(elements.checkedCard, decision.checked.status);

  const aiAnswer = data.ai_answer || {};
  if (elements.aiAnswerBlock && aiAnswer.enabled) {
    const usage = aiAnswer.usage || {};
    elements.aiAnswerBlock.hidden = false;
    elements.aiAnswerBlock.classList.toggle("has-error", aiAnswer.status === "error");
    if (aiAnswer.status === "generated" && aiAnswer.answer) {
      elements.aiAnswerTitle.textContent = "판정 일치 확인 AI 설명";
      elements.aiAnswerStatus.textContent = "상태 일치 확인";
      elements.aiAnswerText.textContent = aiAnswer.answer;
      elements.aiAnswerMeta.textContent = `${aiAnswer.model || "Chat model"} · ${Number(usage.total_tokens || 0).toLocaleString()} tokens · ${aiAnswer.iterations || 0}회 반복`;
    } else if (aiAnswer.status === "error") {
      elements.aiAnswerTitle.textContent = "AI 설명 생성 실패";
      elements.aiAnswerStatus.textContent = aiAnswer.error_code === "invalid_model_response"
        ? "응답 검증 실패"
        : "API 호출 실패";
      elements.aiAnswerText.textContent = aiAnswer.warning || "Chat API 응답을 받지 못했습니다. 서버 설정과 로그를 확인하세요.";
      elements.aiAnswerMeta.textContent = `${aiAnswer.model || "Chat model"} · ${Number(usage.total_tokens || 0).toLocaleString()} tokens · ${aiAnswer.iterations || 0}회 반복`;
    } else {
      elements.aiAnswerTitle.textContent = "규칙 기반 설명";
      elements.aiAnswerStatus.textContent = "규칙 답변 대체";
      elements.aiAnswerText.textContent = aiAnswer.answer || "규칙 기반 판정 결과를 확인하세요.";
      elements.aiAnswerMeta.textContent = `${aiAnswer.model || "Chat model"} · ${Number(usage.total_tokens || 0).toLocaleString()} tokens · ${aiAnswer.iterations || 0}회 반복`;
    }
  } else if (elements.aiAnswerBlock) {
    elements.aiAnswerBlock.hidden = true;
    elements.aiAnswerBlock.classList.remove("has-error");
    elements.aiAnswerTitle.textContent = "판정 일치 확인 AI 설명";
    elements.aiAnswerText.textContent = "";
    elements.aiAnswerMeta.textContent = "";
  }

  const originTitle = countryChecks.origin_country_name ? `${countryChecks.origin_country_name} 출발 추가 규정` : "출발국 추가 규정";
  const destinationTitle = countryChecks.destination_country_name ? `${countryChecks.destination_country_name} 입국 확인` : "도착국 입국 확인";
  const sections = [
    renderListSection("노선 자동 판별 안내", countryChecks.route_warnings, "missing-section"),
    renderListSection("추가로 확인할 정보", decision.missing_information, "missing-section"),
    renderListSection("기내 반입 판정", decision.carry_on.reasons),
    renderListSection("위탁 수하물 판정", decision.checked.reasons),
    renderListSection("지켜야 할 조건", decision.conditions),
    renderListSection("예외 및 주의사항", decision.exceptions),
    renderCountryRuleSection(originTitle, countryChecks.aviation_status, countryChecks.aviation_rules),
    renderCountryRuleSection(destinationTitle, countryChecks.entry_status, countryChecks.entry_rules),
    renderListSection("경유지 재검색 안내", countryChecks.transit_notices, "missing-section"),
  ];
  elements.resultSections.innerHTML = sections.join("");

  const sources = uniqueSources(decision.sources, countryChecks);
  if (sources.length) {
    elements.sourceBlock.innerHTML = `<h3>적용한 공식 근거</h3>${sources.map((source) => `
      <a class="source-link" href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">
        [${escapeHtml(source.rule_id)}] ${escapeHtml(source.title)}
        <span>확인일 ${escapeHtml(source.verified_date)} · 공식 원문 열기 ↗</span>
      </a>`).join("")}`;
  } else {
    elements.sourceBlock.innerHTML = "";
  }

  setView("result");
  if (window.matchMedia("(max-width: 900px)").matches) {
    elements.resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function submitForm(event) {
  event.preventDefault();
  clearError();
  if (!elements.form.reportValidity()) return;

  const payload = buildPayload();
  savePreferences();
  setView("loading");
  elements.submitButton.disabled = true;

  try {
    const response = await fetch("/api/decide", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "판정 결과를 가져오지 못했습니다.");
    renderResult(data);
  } catch (error) {
    setView("empty");
    showError(error.message || "연결 중 오류가 발생했습니다.");
  } finally {
    elements.submitButton.disabled = false;
  }
}

function savePreferences() {
  const preference = {
    airline: elements.airline.value,
    route_type: elements.routeType.value,
    origin_country: elements.originCountry.value,
    destination_country: elements.destinationCountry.value,
    transit_country: elements.transitCountry.value,
  };
  localStorage.setItem("carrycheck-country-preferences", JSON.stringify(preference));
}

function restorePreferences() {
  try {
    const preference = JSON.parse(localStorage.getItem("carrycheck-country-preferences"));
    if (!preference) return;
    elements.airline.value = preference.airline || "";
    elements.routeType.value = preference.route_type || "";
    elements.originCountry.value = preference.origin_country || "";
    elements.destinationCountry.value = preference.destination_country || "";
    elements.transitCountry.value = preference.transit_country || "";
  } catch {
    localStorage.removeItem("carrycheck-country-preferences");
  }
}

function inferRouteFromCountries() {
  if (!elements.originCountry.value || !elements.destinationCountry.value) return;
  elements.routeType.value = elements.originCountry.value === elements.destinationCountry.value ? "domestic" : "international";
}

function resetForm() {
  elements.form.reset();
  clearError();
  setView("empty");
  localStorage.removeItem("carrycheck-country-preferences");
  elements.airline.focus();
}

elements.form.addEventListener("submit", submitForm);
elements.resetButton.addEventListener("click", resetForm);
[elements.originCountry, elements.destinationCountry].forEach((element) => {
  element.addEventListener("change", () => {
    inferRouteFromCountries();
    savePreferences();
  });
});
[elements.airline, elements.routeType, elements.transitCountry].forEach((element) => element.addEventListener("change", savePreferences));
loadOptions();
