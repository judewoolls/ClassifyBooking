function navigateTo(rawDate) {
    const d = new Date(rawDate); // rawDate can be a date string or object
    if (isNaN(d)) {
        console.error("Invalid date:", rawDate);
        return;
    }

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const formattedDate = `${year}-${month}-${day}`;

    console.log("Navigating to:", formattedDate);
    window.location.href = `/booking/${formattedDate}/`;
}

function navigateToCurrentDate() {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0'); // Months are zero-based
    const day = String(d.getDate()).padStart(2, '0');
    const formattedDate = `${year}-${month}-${day}`;
    window.location.href = `/booking/${formattedDate}/`;
}


document.addEventListener('DOMContentLoaded', function() {
    let titles = document.querySelectorAll('.event-title')
    titles.forEach(title => {
        title.addEventListener('mouseover', function() {
            title.classList.add('text-info');
        });
        title.addEventListener('mouseout', function() {
            title.classList.remove('text-info');
        });
    });
});