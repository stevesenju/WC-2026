document.addEventListener("DOMContentLoaded", () => {
    const serviceId = document.getElementById("current-service-id").value;
    const dateInput = document.getElementById("booking-date");
    const displayDate = document.getElementById("display-date");
    
    const stylistSection = document.getElementById("stylist-section");
    const exactMatchesContainer = document.getElementById("exact-matches-container");
    const closeMatchesContainer = document.getElementById("close-matches-container");
    const closeMatchesGrid = document.getElementById("close-matches-grid");
    
    const profileBox = document.getElementById("stylist-profile");
    const displayPrice = document.getElementById("display-price");
    const displayMobility = document.getElementById("display-mobility");
    const displayPortfolio = document.getElementById("display-portfolio");
    
    const contactSection = document.getElementById("contact-section");
    const locationGroup = document.getElementById("location-group");
    const lieuSelect = document.getElementById("lieu-select");
    const adresseGroup = document.getElementById("adresse-group");
    
    const timePanel = document.getElementById("time-panel");
    const timeSlotsContainer = document.getElementById("time-slots");
    const confirmBtn = document.getElementById("confirm-btn");
    const btnPrice = document.getElementById("btn-price");

    const hiddenStylist = document.getElementById("hidden-stylist");
    const hiddenDate = document.getElementById("hidden-date");
    const hiddenTime = document.getElementById("hidden-time");

    let activeDateStr = "";

    // 1. DATE PICKER TRIGGER
    dateInput.addEventListener("change", (e) => {
        activeDateStr = e.target.value;
        hiddenDate.value = activeDateStr;
        displayDate.innerText = activeDateStr;
        
        // Reset UI
        profileBox.style.display = "none";
        contactSection.style.display = "none";
        timePanel.style.opacity = "0.5";
        timePanel.style.pointerEvents = "none";
        timeSlotsContainer.innerHTML = "<p class='text-muted text-small'>Recherche des disponibilités...</p>";
        
        fetchStylists(activeDateStr);
    });

    // 2. FETCH STYLISTS FROM PYTHON
    function fetchStylists(dateStr) {
        fetch(`/api/available-stylists/${serviceId}/${dateStr}`)
            .then(res => res.json())
            .then(data => {
                stylistSection.style.display = "block";
                exactMatchesContainer.innerHTML = "";
                closeMatchesGrid.innerHTML = "";

                // Render Exact Matches
                if (data.exact_matches.length > 0) {
                    data.exact_matches.forEach(stylist => {
                        exactMatchesContainer.appendChild(createStylistBtn(stylist, false));
                    });
                } else {
                    exactMatchesContainer.innerHTML = "<p class='text-muted'>Personne n'est disponible à cette date exacte.</p>";
                }

                // Render Close Matches if Python sent them
                if (data.close_matches.length > 0) {
                    closeMatchesContainer.style.display = "block";
                    data.close_matches.forEach(stylist => {
                        closeMatchesGrid.appendChild(createStylistBtn(stylist, true));
                    });
                } else {
                    closeMatchesContainer.style.display = "none";
                }
            });
    }

    // Helper: Build the HTML button for a stylist
    function createStylistBtn(stylist, isCloseMatch) {
        const btn = document.createElement("button");
        btn.className = "stylist-btn";
        
        let html = `<span>${stylist.alias}</span>`;
        if (isCloseMatch) {
            html += `<span class="close-match-badge">Dispo le ${stylist.date_dispo}</span>`;
        }
        btn.innerHTML = html;

        btn.addEventListener("click", () => {
            // Remove active from all
            document.querySelectorAll(".stylist-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // If it's a close match, update the working date!
            if (isCloseMatch) {
                activeDateStr = stylist.date_dispo;
                hiddenDate.value = activeDateStr;
                displayDate.innerText = activeDateStr;
                dateInput.value = activeDateStr; // Visually update the date picker
            }

            activateStylistProfile(stylist);
            fetchAvailableTimes(stylist.id, activeDateStr);
        });

        return btn;
    }

    // 3. SHOW PROFILE & MOBILITY LOGIC
    function activateStylistProfile(stylist) {
        hiddenStylist.value = stylist.id;
        displayPrice.innerText = `${stylist.prix.toFixed(2)} $`;
        btnPrice.innerText = stylist.prix.toFixed(2);
        
        let mobilityText = "Studio Uniquement";
        if(stylist.deplacement_pref === 'Domicile') mobilityText = "À Domicile Uniquement";
        if(stylist.deplacement_pref === 'Both') mobilityText = "Studio ou Domicile";
        displayMobility.innerText = `📍 ${mobilityText}`;

        displayPortfolio.innerHTML = "";
        if (stylist.images.length > 0) {
            stylist.images.forEach(imgUrl => {
                let img = document.createElement("img");
                img.src = imgUrl;
                displayPortfolio.appendChild(img);
            });
        }

        // Handle Form Logic
        if (stylist.deplacement_pref === "Both" || stylist.deplacement_pref === "Domicile") {
            locationGroup.style.display = "block";
            lieuSelect.value = stylist.deplacement_pref === "Domicile" ? "domicile" : "studio";
            lieuSelect.dispatchEvent(new Event('change'));
        } else {
            locationGroup.style.display = "none";
            adresseGroup.style.display = "none";
            document.querySelector("input[name='client_adresse']").required = false;
        }

        profileBox.style.display = "block";
        contactSection.style.display = "block";
    }

    // Address toggle
    lieuSelect.addEventListener("change", (e) => {
        if (e.target.value === "domicile") {
            adresseGroup.style.display = "block";
            document.querySelector("input[name='client_adresse']").required = true;
        } else {
            adresseGroup.style.display = "none";
            document.querySelector("input[name='client_adresse']").required = false;
        }
    });

    // 4. FETCH TIMES
    function fetchAvailableTimes(stylistId, dateStr) {
        timePanel.style.opacity = "1";
        timePanel.style.pointerEvents = "auto";
        timeSlotsContainer.innerHTML = "<p class='text-muted text-small'>Chargement...</p>";
        
        fetch(`/api/times/${stylistId}/${dateStr}`)
            .then(res => res.json())
            .then(data => {
                timeSlotsContainer.innerHTML = "";
                data.times.forEach(time => {
                    const slot = document.createElement("div");
                    slot.className = "time-slot";
                    slot.innerText = time;
                    slot.addEventListener("click", () => {
                        document.querySelectorAll(".time-slot").forEach(s => s.classList.remove("selected"));
                        slot.classList.add("selected");
                        hiddenTime.value = time;
                        confirmBtn.disabled = false;
                    });
                    timeSlotsContainer.appendChild(slot);
                });
            });
    }
});