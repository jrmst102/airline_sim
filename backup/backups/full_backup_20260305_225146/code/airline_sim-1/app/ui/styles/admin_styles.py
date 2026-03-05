# filepath: /workspaces/airline_sim/app/ui/styles/admin_styles.py

# Admin Dashboard Styles
body {
    font-family: Arial, sans-serif;
    background-color: #f4f4f4;
    margin: 0;
    padding: 20px;
}

.header {
    background-color: #007bff;
    color: white;
    padding: 10px 20px;
    text-align: center;
}

.container {
    max-width: 1200px;
    margin: auto;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.button {
    background-color: #28a745;
    color: white;
    border: none;
    padding: 10px 15px;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.3s;
}

.button:hover {
    background-color: #218838;
}

.table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}

.table th, .table td {
    border: 1px solid #ddd;
    padding: 8px;
}

.table th {
    background-color: #007bff;
    color: white;
}

.table tr:nth-child(even) {
    background-color: #f2f2f2;
}

.table tr:hover {
    background-color: #ddd;
}

.footer {
    text-align: center;
    margin-top: 20px;
    font-size: 0.9em;
    color: #666;
}