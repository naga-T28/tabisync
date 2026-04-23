fetch(window.location.href, {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": "{{ csrf_token }}"
    },
    body: JSON.stringify({
        action: "save_want_to_go",
        place_id: selectedPlace.place_id,
        name: document.getElementById("placeName").value,
        address: document.getElementById("placeAddress").value,
        lat: selectedPlace.geometry.location.lat(),
        lng: selectedPlace.geometry.location.lng(),
        memo: document.getElementById("memo").value,
        day: document.getElementById("plannedDay").value
    })
})