/**
 * AirGuard - Air Quality Index Application
 * Handles data loading, card rendering, and user interactions
 */

// ===== CONSTANTS =====
const DEFAULT_CITY = "Kuala Lumpur";
const IP_API_URL = "https://ipapi.co/json/";
const IP_API_TIMEOUT = 2000; // 2 seconds

// User's country (from IP geolocation)
let userCountry = null;

// ===== UTILITIES =====

const getElement = (id) => document.getElementById(id);

const escapeHtml = (str) => {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
};

const parseContainer = (containerId) => typeof containerId === 'string' 
    ? document.getElementById(containerId) 
    : containerId;

const showError = (msg) => {
    const el = getElement("search-error");
    el.textContent = msg;
    el.classList.toggle("show", msg);
};

const parseResponse = (resp) => resp.status === "error" 
    ? { success: false, error: resp.message || "Unknown error" }
    : { success: true, data: resp.data };


const showSubscriptionMessage = (msg, type = "success") => {
    const el = getElement("subscription-message");
    if (!el) return;

    el.textContent = msg;
    el.classList.remove("success", "error", "show");

    if (!msg) return;
    el.classList.add(type, "show");
};


// ===== CARD HTML GENERATION =====

const buildAdviceHtml = (advice) => {
    const items = Array.isArray(advice) ? advice : [advice];
    return items
        .filter(a => a)
        .map(a => `<li>${escapeHtml(a)}</li>`)
        .join("");
};

const createDetailedCardHtml = (city) => `
    ${city._crown ? '<div class="crown-badge">👑</div>' : ''}
    <div class="card-top">
        <h2 class="city-name-container">
            <span class="city-name-text">${city.city}</span>
             ${city.is_local ? '<span class="current-location-text">(your current location)</span>' : ''}
        </h2> 
        <div class="stats-row">
            <div class="stat-item">
                <p class="aqi-value">${escapeHtml(city.aqi)}</p>
                <p class="stat-label">AQI</p>
            </div>
            <div class="stat-item">
                <p class="level-value">${escapeHtml(city.level)}</p>
                <p class="stat-label">Level</p>
            </div>
            <div class="stat-item">
                <p class="update-time">${escapeHtml(city.time_s) || 'N/A'}</p>
                <p class="stat-label">Updated</p>
            </div>
        </div>
        ${city.dominentpol ? `<p class="pollutant"><strong>Main Pollutant:</strong> ${escapeHtml(city.dominentpol)}</p>` : ''}
    </div>
    <div class="card-bottom">
        <ul class="advice-list">${buildAdviceHtml(city.advice || "No advice available")}</ul>
    </div>
`;

const createPopularCardHtml = (city) => `
    <h3>${escapeHtml(city.city)}</h3>
    <p class="aqi-value">${escapeHtml(city.aqi)}</p>
    <p class="level">${escapeHtml(city.level)}</p>
    <p style="font-size: 0.75rem; margin-top: auto; opacity: 0.8;">Click for details</p>
`;


// ===== CARD RENDERING =====

const renderCards = (cities, containerId, cardType = "detailed") => {
    const container = parseContainer(containerId);
    if (!container) return;
    
    container.innerHTML = "";
    cities.forEach(city => {
        const card = document.createElement("div");
        card.className = `card ${cardType}-card ${city._class || ''}`;
        card.style.backgroundColor = city.color;
        card.style.color = city.text_color;
        card.innerHTML = cardType === "detailed" 
            ? createDetailedCardHtml(city) 
            : createPopularCardHtml(city);
        
        // Add click handler for popular cards to show details
        if (cardType === "popular") {
            card.style.cursor = "pointer";
            card.addEventListener("click", () => showCityDetails(city.city));
        }
        
        container.appendChild(card);
    });
};

const renderDetailedCards = (cities, containerId) => {
    const container = parseContainer(containerId);
    if (container) container.classList.remove("comparison-mode");
    
    // Mark better AQI with crown
    if (cities.length > 1) {
        const aqi1 = parseInt(cities[0].aqi) || 999;
        const aqi2 = parseInt(cities[1].aqi) || 999;
        
        if (aqi1 <= aqi2) {
            cities[0]._crown = true;
            cities[0]._class = "better-aqi";
            cities[1]._class = "worse-aqi";
        } else {
            cities[0]._class = "worse-aqi";
            cities[1]._crown = true;
            cities[1]._class = "better-aqi";
        }
    }
    
    renderCards(cities, containerId, "detailed");
    if (cities.length > 1 && container) container.classList.add("comparison-mode");
};


// ===== API CALLS =====

const fetchAPI = async (url) => {
    try {
        const res = await fetch(url);
        return parseResponse(await res.json());
    } catch (err) {
        console.error(err);
        return { success: false, error: "Network error" };
    }
};

const fetchWithTimeout = async (url, timeout) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    try {
        const res = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        return await res.json();
    } catch (err) {
        clearTimeout(timeoutId);
        return null;
    }
};

const getLocationFromIP = async () => {
    try {
        const data = await fetchWithTimeout(IP_API_URL, IP_API_TIMEOUT);
        // Store user's country for analytics
        userCountry = data?.country_name || null;
        return data?.city || null;
    } catch {
        return null;
    }
};


// ===== DATA LOADING =====

const loadAQIData = async (url, containerId, cardType = "detailed", onSuccess = null) => {
    const parsed = await fetchAPI(url);
    if (!parsed.success) {
        showError(parsed.error);
        return;
    }
    if (onSuccess) {
        onSuccess(parsed.data);
    } else {
        renderCards([parsed.data], containerId, cardType);
    }
};

const loadLocalAQI = async () => {
    // Build URL with user_country if available
    const buildAqiUrl = (city, source) => {
        let url = `/api/aqi?city=${encodeURIComponent(city)}&source=${source}`;
        if (userCountry) url += `&user_country=${encodeURIComponent(userCountry)}`;
        return url;
    };
    
    // Try to get IP location FIRST (non-blocking, with timeout)
    const ipCity = await getLocationFromIP();
    
    // Determine which city to show
    const targetCity = ipCity || DEFAULT_CITY;
    
    // Fetch AQI for target city (now userCountry is set if IP lookup succeeded)
    const cityAQI = await fetchAPI(buildAqiUrl(targetCity, 'auto'));
    
    if (cityAQI.success) {
        cityAQI.data.is_local = true;
        renderDetailedCards([cityAQI.data], "aqi-card-container");
    } else if (ipCity && ipCity !== DEFAULT_CITY) {
        // IP city failed, fallback to default
        showError(`No AQI data for ${ipCity}. Showing ${DEFAULT_CITY}.`);
        const defaultAQI = await fetchAPI(buildAqiUrl(DEFAULT_CITY, 'auto'));
        if (defaultAQI.success) {
            defaultAQI.data.is_local = true;
            renderDetailedCards([defaultAQI.data], "aqi-card-container");
        } else {
            showError(defaultAQI.error);
        }
    } else {
        showError(cityAQI.error);
    }
};

const loadPopularCities = async () => {
    await loadAQIData("/api/popular", "popular-container", "popular", (data) => {
        const container = getElement("popular-container");
        container.innerHTML = "";
        
        // Split cities into two rows
        const mid = Math.ceil(data.length / 2);
        [data.slice(0, mid), data.slice(mid)].forEach(row => {
            if (row.length) {
                const rowDiv = document.createElement("div");
                rowDiv.className = "popular-row";
                renderCards(row, rowDiv, "popular");
                container.appendChild(rowDiv);
            }
        });
    });
};


// ===== USER INTERACTIONS =====

const showCityDetails = async (cityName) => {
    showError("");
    let url = `/api/aqi?city=${encodeURIComponent(cityName)}`;
    if (userCountry) url += `&user_country=${encodeURIComponent(userCountry)}`;
    const parsed = await fetchAPI(url);
    if (!parsed.success) {
        showError(parsed.error);
        return;
    }
    renderDetailedCards([parsed.data], "aqi-card-container");
};

const handleSearchCompare = async () => {
    showError("");
    const city1 = getElement("city1").value.trim();
    const city2 = getElement("city2").value.trim();
    
    if (!city1) {
        showError("Please enter at least one city");
        return;
    }
    
    const url = city2 
        ? `/api/compare?city1=${encodeURIComponent(city1)}&city2=${encodeURIComponent(city2)}${userCountry ? '&user_country=' + encodeURIComponent(userCountry) : ''}`
        : `/api/aqi?city=${encodeURIComponent(city1)}${userCountry ? '&user_country=' + encodeURIComponent(userCountry) : ''}`;
    
    const parsed = await fetchAPI(url);
    if (!parsed.success) {
        showError(parsed.error);
        return;
    }
    
    const data = parsed.data;
    let cards = [];
    
    if (city2) {
        if (!data.city1 || !data.city2 || data.city1.error || data.city2.error) {
            showError("One or both cities not found");
            return;
        }
        cards = [{...data.city1, is_local: false}, {...data.city2, is_local: false}];
    } else {
        cards = [{...data, is_local: false}];
    }
    
    renderDetailedCards(cards, "aqi-card-container");
};



const validateSubscriptionForm = (formData) => {
    if (!formData.username.trim()) return "Username is required";
    if (!formData.email.trim()) return "Email is required";
    if (!/^\S+@\S+\.\S+$/.test(formData.email.trim())) return "Please provide a valid email address";
    if (!formData.city.trim()) return "Please select a city";
    if (!formData.alert_time.trim()) return "Alert time is required";
    return null;
};

const handleSubscriptionSubmit = async (event) => {
    event.preventDefault();
    showSubscriptionMessage("");

    const submitBtn = getElement("sub-submit");
    const payload = {
        username: getElement("sub-username")?.value || "",
        email: getElement("sub-email")?.value || "",
        city: getElement("sub-city")?.value || "",
        alert_time: getElement("sub-time")?.value || "",
    };

    const validationError = validateSubscriptionForm(payload);
    if (validationError) {
        showSubscriptionMessage(validationError, "error");
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting...";

    try {
        const res = await fetch("/api/subscriptions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const parsed = parseResponse(await res.json());
        if (!parsed.success) {
            showSubscriptionMessage(parsed.error || "Unable to register subscription", "error");
            return;
        }

        showSubscriptionMessage(parsed.data.message || "Subscription registered successfully.", "success");
        getElement("subscription-form")?.reset();
    } catch (err) {
        console.error(err);
        showSubscriptionMessage("Network error while creating subscription", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Subscribe";
    }
};

// ===== INITIALIZATION =====

window.onload = () => {
    // Load local AQI and popular cities in PARALLEL (no await)
    loadLocalAQI();
    loadPopularCities();
    
    // Setup search button
    getElement("go-btn").addEventListener("click", handleSearchCompare);
    
    // Setup city input fields - clear error on input, search on Enter
    [getElement("city1"), getElement("city2")].forEach(input => {
        input.addEventListener("input", () => showError(""));
        input.addEventListener("keyup", e => {
            if (e.key === "Enter") handleSearchCompare();
        });
    });

    const subscriptionForm = getElement("subscription-form");
    if (subscriptionForm) {
        subscriptionForm.addEventListener("submit", handleSubscriptionSubmit);
    }
};
