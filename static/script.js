"use strict";

const API_URL = "/api/dashboard";

let topProductsChart = null;
let salesChart = null;

const rupiah = new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0
});

const numberFormat = new Intl.NumberFormat("id-ID");

function formatRupiah(value) {
    return rupiah.format(Number(value) || 0);
}

function formatNumber(value) {
    return numberFormat.format(Number(value) || 0);
}

function showError(message) {
    const errorBox = document.getElementById("error-message");

    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
}

function hideError() {
    document.getElementById("error-message")
        .classList.add("hidden");
}

function setLoading(isLoading) {
    const button = document.getElementById("refresh-btn");
    const loading = document.getElementById("loading");

    button.disabled = isLoading;
    loading.classList.toggle("hidden", !isLoading);
}

async function loadDashboard() {
    setLoading(true);
    hideError();

    try {
        const response = await fetch(API_URL, {
            headers: {
                "Accept": "application/json"
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Gagal mengambil data dashboard."
            );
        }

        renderSummary(data.summary);
        renderLowStock(data.low_stock);
        renderTopProducts(data.top_products);
        renderSalesTrend(data.daily_sales);

        document.getElementById("last-updated").textContent =
            "Terakhir diperbarui: " +
            new Date().toLocaleString("id-ID");

    } catch (error) {
        console.error("Dashboard error:", error);

        showError(
            error.message ||
            "Tidak dapat memuat data. Periksa koneksi Flask."
        );

    } finally {
        setLoading(false);
    }
}

function renderSummary(summary) {
    document.getElementById("total-revenue").textContent =
        formatRupiah(summary.total_revenue);

    document.getElementById("total-transactions").textContent =
        formatNumber(summary.total_transactions);

    document.getElementById("total-products").textContent =
        formatNumber(summary.total_products);
}

function renderLowStock(products) {
    const tbody = document.getElementById("stock-table-body");
    const stockCount = document.getElementById("low-stock-count");
    const stockLabel = document.getElementById("stock-label");

    stockCount.textContent = formatNumber(products.length);
    stockLabel.textContent =
        `${formatNumber(products.length)} produk`;

    tbody.replaceChildren();

    if (products.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.className = "empty-cell";
        cell.textContent = "Tidak ada produk dengan stok rendah.";

        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }

    products.forEach((product) => {
        const row = document.createElement("tr");

        const idCell = document.createElement("td");
        idCell.textContent = product.product_id;

        const nameCell = document.createElement("td");
        nameCell.className = "product-name";
        nameCell.textContent = product.product_name;

        const categoryCell = document.createElement("td");
        categoryCell.textContent = product.category;

        const stockCell = document.createElement("td");
        stockCell.className = "stock-number";
        stockCell.textContent =
            `${formatNumber(product.stock_qty)} unit`;

        const statusCell = document.createElement("td");
        const badge = document.createElement("span");

        badge.className = "status-pill";

        if (product.stock_qty <= 7) {
            badge.textContent = "Stok kritis";
        } else {
            badge.classList.add("medium");
            badge.textContent = "Stok rendah";
            stockCell.classList.add("medium");
        }

        statusCell.appendChild(badge);

        row.append(
            idCell,
            nameCell,
            categoryCell,
            stockCell,
            statusCell
        );

        tbody.appendChild(row);
    });
}

function renderTopProducts(products) {
    const canvas = document.getElementById("top-products-chart");

    if (topProductsChart) {
        topProductsChart.destroy();
    }

    topProductsChart = new Chart(canvas, {
        type: "bar",

        data: {
            labels: products.map(
                (product) => product.product_name
            ),

            datasets: [{
                label: "Unit terjual",

                data: products.map(
                    (product) => Number(product.total_sold)
                ),

                backgroundColor: [
                    "#6758e8",
                    "#8b7ff0",
                    "#a79cf5",
                    "#c0b9fa",
                    "#d8d3fd"
                ],

                borderRadius: 7,
                borderSkipped: false,
                maxBarThickness: 38
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    callbacks: {
                        label: (context) =>
                            `${formatNumber(context.raw)} unit terjual`
                    }
                }
            },

            scales: {
                x: {
                    grid: {
                        display: false
                    },

                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                },

                y: {
                    beginAtZero: true,

                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

function renderSalesTrend(dailySales) {
    const canvas = document.getElementById("sales-chart");

    if (salesChart) {
        salesChart.destroy();
    }

    salesChart = new Chart(canvas, {
        type: "line",

        data: {
            labels: dailySales.map((item) => {
                const parts = item.sale_date.split("-");
                return `${parts[2]}/${parts[1]}/${parts[0]}`;
            }),

            datasets: [{
                label: "Omzet harian",

                data: dailySales.map(
                    (item) => Number(item.daily_revenue)
                ),

                borderColor: "#18a878",
                backgroundColor: "rgba(24, 168, 120, 0.10)",

                fill: true,
                tension: 0.35,
                borderWidth: 2.5,

                pointRadius: dailySales.length > 20 ? 0 : 3,
                pointHoverRadius: 5
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    callbacks: {
                        label: (context) =>
                            formatRupiah(context.raw)
                    }
                }
            },

            scales: {
                x: {
                    grid: {
                        display: false
                    },

                    ticks: {
                        maxTicksLimit: 7,
                        maxRotation: 0,
                        font: {
                            size: 10
                        }
                    }
                },

                y: {
                    beginAtZero: true,

                    ticks: {
                        maxTicksLimit: 5,

                        callback: (value) => {
                            if (value >= 1000000) {
                                return (
                                    "Rp" +
                                    (value / 1000000).toLocaleString(
                                        "id-ID"
                                    ) +
                                    " jt"
                                );
                            }

                            if (value >= 1000) {
                                return (
                                    "Rp" +
                                    (value / 1000).toLocaleString(
                                        "id-ID"
                                    ) +
                                    " rb"
                                );
                            }

                            return "Rp" + value;
                        }
                    }
                }
            }
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("refresh-btn")
        .addEventListener("click", loadDashboard);

    loadDashboard();
});