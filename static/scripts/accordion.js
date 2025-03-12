// function toggleAccordion(id) {
//     var content = document.getElementById(id);
//     // Use computed style instead of inline style for a reliable check.
//     var computedDisplay = window.getComputedStyle(content).display;
//     if (computedDisplay === "none") {
//         content.style.display = "table-row-group";
//     } else {
//         content.style.display = "none";
//     }
    
//     // Check each accordion-content using computed style.
//     var accordions = document.querySelectorAll('.accordion-content');
//     var anyExpanded = false;
//     accordions.forEach(function(acc) {
//         if (window.getComputedStyle(acc).display !== "none") {
//             anyExpanded = true;
//         }
//     });
    
//     // Loop through extra columns; if any accordion is expanded, show them.
//     var extraCols = document.querySelectorAll('.extra-col');
//     extraCols.forEach(function(col) {
//         col.style.display = anyExpanded ? "table-cell" : "none";
//     });
// }
function toggleAccordion(id) {
    var content = document.getElementById(id);
    var button = document.getElementById('button-' + id);
    // Use computed style instead of inline style for a reliable check.
    var computedDisplay = window.getComputedStyle(content).display;
    if (computedDisplay === "none") {
        content.style.display = "table-row-group";
        button.textContent = "Collapse";
    } else {
        content.style.display = "none";
        button.textContent = "Expand";
    }
    
    // Check each accordion-content using computed style.
    var accordions = document.querySelectorAll('.accordion-content');
    var anyExpanded = false;
    accordions.forEach(function(acc) {
        if (window.getComputedStyle(acc).display !== "none") {
            anyExpanded = true;
        }
    });
    
    // Loop through extra columns; if any accordion is expanded, show them.
    var extraCols = document.querySelectorAll('.extra-col');
    extraCols.forEach(function(col) {
        col.style.display = anyExpanded ? "table-cell" : "none";
    });
}