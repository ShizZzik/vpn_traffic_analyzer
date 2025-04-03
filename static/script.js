document.addEventListener("DOMContentLoaded", () => {
    const tbody = document.getElementById("trafficBody");
    const errorDiv = document.getElementById("error");

    // Функция для преобразования байтов в читаемый формат
    function formatBytes(bytes) {
        if (bytes === 0) return "0 B";
        const units = ["B", "KiB", "MiB", "GiB"];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(2) + " " + units[i];
    }

    fetch("/api/traffic")
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.length === 0) {
                errorDiv.textContent = "Данные не найдены. Проверьте конфигурацию сервера или users.json.";
                return;
            }
            data.forEach(user => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${user.clientName}</td>
                    <td>${user.allowedIps || "N/A"}</td>
                    <td>${user.dataReceived}</td>
                    <td>${user.dataSent}</td>
                    <td>${formatBytes(user.transferRx)}</td>
                    <td>${formatBytes(user.transferTx)}</td>
                    <td>${user.latestHandshake}</td>
                    <td>${user.endpoint}</td>
                `;
                tbody.appendChild(row);
            });
        })
        .catch(error => {
            errorDiv.textContent = `Ошибка загрузки данных: ${error.message}`;
            console.error("Fetch error:", error);
        });
});
