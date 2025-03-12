const searchInput = document.getElementById('zipcode-search');
const autocompleteList = document.getElementById('autocomplete-list');

// Autocomplete functionality
searchInput.addEventListener('input', function () {
    const query = this.value;
    if (query.length > 0) { // Fetch suggestions if input has more than 2 characters
        fetch(`/autocomplete_zipcode?query=${query}`)
            .then(response => response.json())
            .then(data => {
                autocompleteList.innerHTML = ''; // Clear any existing items

                data.forEach(zipcode => {
                    const item = document.createElement('div');
                    item.textContent = zipcode;
                    item.addEventListener('click', function () {
                        searchInput.value = zipcode;
                        autocompleteList.innerHTML = ''; // Close the list after selection
                    });
                    autocompleteList.appendChild(item);
                });
            });
    } else {
        autocompleteList.innerHTML = ''; // Clear list if input is too short
    }
});

// Close the autocomplete dropdown when clicking outside
document.addEventListener('click', function (event) {
    if (!searchInput.contains(event.target) && !autocompleteList.contains(event.target)) {
        autocompleteList.innerHTML = ''; // Close the list when clicking outside
    }
});

// Handle form submission
document.getElementById('search-form').addEventListener('submit', function (event) {
    const query = searchInput.value;
    if (!query) {
        event.preventDefault(); // Prevent submission if no zip code is entered
        alert("Please enter a zip code to search.");
    }
});