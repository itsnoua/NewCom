/**
 * MapEngine
 * Handles MapLibre Initialization, 3D Rendering (Extrusion), and Interactions
 */

const DATA_URL = 'data/Final_Buildings_Compliance.geojson';

// Palette defined in user prompt
const PALETTE = {
    compliant: '#00ff41',    // Neon Green
    compliantBuffer: '#ffa500', // Orange Warning
    nonCompliant: '#ff3131', // Deep Red
    default: '#aaaaaa'
};

let map;
let dataHandler;
let gaugeChart;
let hoveredStateId = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Init Data layer (Cache locally)
    dataHandler = new DataHandler();
    const geojson = await dataHandler.loadData(DATA_URL);

    // 2. Setup UI
    initGaugeChart();

    if (geojson) {
        // 3. Render 3D Map
        initMap(geojson);
        // 4. Initial KPI Population
        updateDashboard('all');
        // 5. Setup Dropdown logic
        setupDropdown();
    } else {
        alert("تعذر قراءة ملف البيانات. تأكد من تشغيل الخادم المحلي.");
    }
});

/**
 * Initialize MapLibre GL 3D Map
 */
function initMap(geojson) {
    map = new maplibregl.Map({
        container: 'map',
        // CartoDB Dark Matter Base map for High Contrast
        style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
        center: [42.505, 18.22], // Center around Abha
        zoom: 13,
        pitch: 55, // 3D Pitch
        bearing: -15,
        antialias: true
    });

    map.on('load', () => {
        // Source
        map.addSource('buildings', {
            type: 'geojson',
            data: geojson,
            generateId: true // Required for hover highlight
        });

        // 3D Extrusion Layer
        map.addLayer({
            'id': 'buildings-3d',
            'type': 'fill-extrusion',
            'source': 'buildings',
            'paint': {
                // Color Logic (Default state)
                'fill-extrusion-color': [
                    'match',
                    ['get', 'Compliance_Status'],
                    'ممتثل', PALETTE.compliant,
                    'ممتثل (تقريبي)', PALETTE.compliantBuffer,
                    'غير ممتثل', PALETTE.nonCompliant,
                    PALETTE.default
                ],
                // Height Logic: 18m for compliant, 15m for approximate, 12m for non-compliant to give dynamic realistic skyline
                'fill-extrusion-height': [
                    'match',
                    ['get', 'Compliance_Status'],
                    'ممتثل', 18,
                    'ممتثل (تقريبي)', 15,
                    'غير ممتثل', 12,
                    10
                ],
                'fill-extrusion-base': 0,
                // Opacity: MapLibre does NOT support data expressions for 3D extrusion opacity, so it must be static
                'fill-extrusion-opacity': 0.9
            }
        });

        setupInteractions();
    });
}

/**
 * Setup Advanced Interactions (Hover, Popup, Clicks)
 */
function setupInteractions() {
    const popup = new maplibregl.Popup({
        closeButton: true,
        closeOnClick: true,
        className: 'custom-popup'
    });

    // Hover Highlight
    map.on('mousemove', 'buildings-3d', (e) => {
        if (e.features.length > 0) {
            map.getCanvas().style.cursor = 'pointer';
            if (hoveredStateId !== null) {
                map.setFeatureState({ source: 'buildings', id: hoveredStateId }, { hover: false });
            }
            hoveredStateId = e.features[0].id;
            map.setFeatureState({ source: 'buildings', id: hoveredStateId }, { hover: true });
        }
    });

    map.on('mouseleave', 'buildings-3d', () => {
        map.getCanvas().style.cursor = '';
        if (hoveredStateId !== null) {
            map.setFeatureState({ source: 'buildings', id: hoveredStateId }, { hover: false });
        }
        hoveredStateId = null;
    });

    // Info Popup on Click
    map.on('click', 'buildings-3d', (e) => {
        if (e.features.length === 0) return;

        const props = e.features[0].properties;
        const streetName = props._clean_street;
        const bldgId = props['رقم المبنى_extracted'] || props.BuildingUID || 'غير محدد';
        const certNo = props['رقم الشهادة'] || props['رقم الشهادة_extracted'] || 'لا يوجد';
        const status = props.Compliance_Status;
        const color = status === 'ممتثل' ? PALETTE.compliant : status === 'ممتثل (تقريبي)' ? PALETTE.compliantBuffer : PALETTE.nonCompliant;

        const html = `
            <div style="border-bottom: 2px solid ${color}; padding-bottom: 5px; margin-bottom: 10px;">
                <h3 style="margin:0; font-size:16px;">تفاصيل المبنى</h3>
                <span style="color:${color}; font-size:13px; font-weight:bold;">${status}</span>
            </div>
            <table class="popup-table">
                <tr><td>الشارع:</td><td>${streetName}</td></tr>
                <tr><td>رقم المبنى:</td><td>${bldgId}</td></tr>
                <tr><td>رقم الشهادة:</td><td>${certNo}</td></tr>
            </table>
            ${certNo !== 'لا يوجد' ? `<a href="#" class="popup-link">🔗 عرض وثيقة الشهادة</a>` : ''}
        `;

        popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
    });
}

/**
 * Setup Sidebar Street Dropdown
 */
function setupDropdown() {
    const streetSelect = document.getElementById('streetSelect');
    const muniSelect = document.getElementById('municipalitySelect');
    const resetBtn = document.getElementById('resetBtn');

    // Populate street dropdown
    dataHandler.getAllStreets().forEach(street => {
        const o = document.createElement('option');
        o.value = street; o.textContent = street;
        streetSelect.appendChild(o);
    });

    // Populate municipality dropdown
    dataHandler.getAllMunicipalities().forEach(muni => {
        const o = document.createElement('option');
        o.value = muni; o.textContent = muni;
        muniSelect.appendChild(o);
    });

    // Street filter change
    streetSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        muniSelect.value = 'all'; // Reset municipality filter
        if (val === 'all') {
            resetMapColors();
            updateDashboard('all', 'street');
            map.flyTo({ center: [42.505, 18.22], zoom: 13, pitch: 55 });
        } else {
            focusOnStreet(val);
        }
    });

    // Municipality filter change
    muniSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        streetSelect.value = 'all'; // Reset street filter
        if (val === 'all') {
            resetMapColors();
            updateDashboard('all', 'municipality');
            map.flyTo({ center: [42.505, 18.22], zoom: 13, pitch: 55 });
        } else {
            focusOnMunicipality(val);
        }
    });

    // Reset Button
    resetBtn.addEventListener('click', () => {
        streetSelect.value = 'all';
        muniSelect.value = 'all';
        resetMapColors();
        updateDashboard('all', 'street');
        map.flyTo({ center: [42.505, 18.22], zoom: 13, pitch: 55 });
    });
}

/**
 * Spatial FlyTo and Highlight Logic
 */
function focusOnStreet(streetName) {
    updateDashboard(streetName, 'street');
    map.setPaintProperty('buildings-3d', 'fill-extrusion-color', [
        'case',
        ['!=', ['get', '_clean_street'], streetName],
        '#222222',
        ['match', ['get', 'Compliance_Status'],
            'ممتثل', PALETTE.compliant,
            'ممتثل (تقريبي)', PALETTE.compliantBuffer,
            'غير ممتثل', PALETTE.nonCompliant,
            PALETTE.default]
    ]);
    map.setPaintProperty('buildings-3d', 'fill-extrusion-height', [
        'case',
        ['!=', ['get', '_clean_street'], streetName],
        2,
        ['match', ['get', 'Compliance_Status'],
            'ممتثل', 18, 'ممتثل (تقريبي)', 15, 'غير ممتثل', 12, 10]
    ]);
    const bbox = dataHandler.getStreetBoundingBox(streetName);
    if (bbox) map.fitBounds(bbox, { padding: 80, pitch: 60, maxZoom: 17, duration: 2500 });
}

function focusOnMunicipality(muniName) {
    updateDashboard(muniName, 'municipality');
    map.setPaintProperty('buildings-3d', 'fill-extrusion-color', [
        'case',
        ['!=', ['get', '_clean_municipality'], muniName],
        '#222222',
        ['match', ['get', 'Compliance_Status'],
            'ممتثل', PALETTE.compliant,
            'ممتثل (تقريبي)', PALETTE.compliantBuffer,
            'غير ممتثل', PALETTE.nonCompliant,
            PALETTE.default]
    ]);
    map.setPaintProperty('buildings-3d', 'fill-extrusion-height', [
        'case',
        ['!=', ['get', '_clean_municipality'], muniName],
        2,
        ['match', ['get', 'Compliance_Status'],
            'ممتثل', 18, 'ممتثل (تقريبي)', 15, 'غير ممتثل', 12, 10]
    ]);
    const bbox = dataHandler.getMunicipalityBoundingBox(muniName);
    if (bbox) map.fitBounds(bbox, { padding: 80, pitch: 60, maxZoom: 15, duration: 2500 });
}

/**
 * Updates KPI Panel and Gauge Chart dynamically
 */
function updateDashboard(filterValue, filterType = 'street') {
    if (filterValue === 'all' && map && map.getLayer('buildings-3d')) {
        resetMapColors();
    }

    const stats = filterType === 'municipality'
        ? dataHandler.getMunicipalityStats(filterValue)
        : dataHandler.getStreetStats(filterValue);

    const total = stats.total || 0;
    const compliant = stats.compliant || 0;
    const compliantBuffer = stats.compliantBuffer || 0;
    const nonCompliant = stats.nonCompliant || 0;

    document.getElementById('kpi-total').textContent = total.toLocaleString();
    document.getElementById('kpi-compliant').textContent = compliant.toLocaleString();
    document.getElementById('kpi-compliant-buffer').textContent = compliantBuffer.toLocaleString();
    document.getElementById('kpi-noncompliant').textContent = nonCompliant.toLocaleString();

    const totalCompliant = compliant + compliantBuffer;
    const ratio = total === 0 ? 0 : Math.round((totalCompliant / total) * 100 * 10) / 10;
    document.getElementById('gaugeValue').textContent = ratio + '%';
    updateGauge(ratio);
}

function resetMapColors() {
    if (!map || !map.getLayer('buildings-3d')) return;
    map.setPaintProperty('buildings-3d', 'fill-extrusion-color', [
        'match', ['get', 'Compliance_Status'],
        'ممتثل', PALETTE.compliant,
        'ممتثل (تقريبي)', PALETTE.compliantBuffer,
        'غير ممتثل', PALETTE.nonCompliant,
        PALETTE.default
    ]);
    map.setPaintProperty('buildings-3d', 'fill-extrusion-height', [
        'match', ['get', 'Compliance_Status'],
        'ممتثل', 18, 'ممتثل (تقريبي)', 15, 'غير ممتثل', 12, 10
    ]);
}

/**
 * Gauge Chart Logic (Chart.js)
 */
function initGaugeChart() {
    const ctx = document.getElementById('gaugeChart').getContext('2d');

    gaugeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['ممتثل', 'غير ممتثل'],
            datasets: [{
                data: [0, 100],
                backgroundColor: [PALETTE.compliant, '#333333'],
                borderWidth: 0,
                cutout: '82%',
                circumference: 180,
                rotation: -90
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            animation: { animateScale: true, animateRotate: true }
        }
    });
}

function updateGauge(ratio) {
    if (gaugeChart) {
        gaugeChart.data.datasets[0].data = [ratio, 100 - ratio];

        let color = PALETTE.compliant;
        if (ratio <= 40) color = PALETTE.nonCompliant;
        else if (ratio < 75) color = '#ffa500'; // Orange Warning

        gaugeChart.data.datasets[0].backgroundColor[0] = color;
        gaugeChart.update();
        document.getElementById('gaugeValue').style.color = color;
    }
}
