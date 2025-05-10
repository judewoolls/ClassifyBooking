const form = document.getElementById("date-form");
const dateList = document.getElementById('date-list');
const addButton = document.getElementById('add');
let deleteButtons = document.querySelectorAll('.delete');
const datesSentOutput = document.getElementById('dates-sent-output');
const datesSentInput = document.getElementById('dates-sent-input');
const datesToAdd = [];

addButton.addEventListener("click", function () {
    console.log("Add button clicked");
    let date = document.getElementById('date-input').value; // Use .value for input fields
    if (date) {
        dateList.innerHTML += `<li>${date} <button class="delete">Delete</button></li>`;
        document.getElementById('date-input').value = ""; // Clear the input field
        deleteButtons = document.querySelectorAll('.delete'); // Update the delete buttons list
        deleteButtons.forEach(button => {
            button.addEventListener('click', function () {
                console.log("Delete button clicked");
                const listItem = this.parentElement; // Get the parent <li> element
                dateList.removeChild(listItem); // Remove the <li> from the list
            });
        });
        datesToAdd.push(date); // Add the date to the array
        datesSentOutput.innerText = `${datesToAdd.join(', ')}`; // Update the displayed dates
        datesSentInput.value = datesToAdd.join(', '); // Update the hidden input value

    } else {
        alert("Please enter a date.");
        return;
    }
});

form.addEventListener('submit', function(event) {
    if (datesToAdd.length === 0) {
        event.preventDefault(); // Prevent form submission if no dates
        alert("Please add dates to duplicate.");
    }
    // The datesInput.value will be submitted with the form
});