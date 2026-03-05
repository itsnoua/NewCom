/**
 * DataHandler Class
 * Handles fetching, Memory Caching, cleaning, and calculating KPIs
 * Separation of Concerns: This module deals only with DATA.
 */
class DataHandler {
    constructor() {
        this.geoData = null;
        this.streetsList = new Set();
        this.municipalityList = new Set();
        this.globalStats = { total: 0, compliant: 0, compliantBuffer: 0, nonCompliant: 0 };
    }

    /**
     * Fetch GeoJSON Data and store in Memory Cache
     * @param {string} url - GeoJSON file path
     */
    async loadData(url) {
        try {
            const response = await fetch(url);
            this.geoData = await response.json();

            // Generate clean street names and cache stats immediately (Worker-like efficiency)
            this.processInitialData();

            return this.geoData;
        } catch (error) {
            console.error("Error loading GeoJSON data:", error);
            return null;
        }
    }

    /**
     * Map over features to inject cleaned names and calculate global stats.
     */
    processInitialData() {
        this.globalStats = { total: 0, compliant: 0, compliantBuffer: 0, nonCompliant: 0 };
        this.streetsList.clear();
        this.municipalityList.clear();

        this.geoData.features.forEach(feature => {
            const props = feature.properties;

            // Clean Street Name
            let streetName = props.Name || props['الشارع'];
            streetName = (streetName && !['nan', 'None', 'NULL', 'null', '<Null>'].includes(streetName))
                ? streetName.trim()
                : 'غير محدد';
            feature.properties._clean_street = streetName;
            this.streetsList.add(streetName);

            // Clean Municipality Name
            let muniName = props['البلدية'];
            muniName = (muniName && !['nan', 'None', 'NULL', 'null', '<Null>', ''].includes(String(muniName).trim()))
                ? String(muniName).trim()
                : 'غير محدد';
            feature.properties._clean_municipality = muniName;
            this.municipalityList.add(muniName);

            // Strip Z-Coordinates
            if (feature.geometry && feature.geometry.coordinates) {
                this._stripZCoordinates(feature.geometry.coordinates);
            }

            // Increment Global KPI
            this.globalStats.total++;
            if (props.Compliance_Status === 'ممتثل') {
                this.globalStats.compliant++;
            } else if (props.Compliance_Status === 'ممتثل (تقريبي)') {
                this.globalStats.compliantBuffer++;
            } else {
                this.globalStats.nonCompliant++;
            }
        });
    }

    /**
     * Get aggregated KPI stats for a specific street or all
     */
    getStreetStats(streetName) {
        if (!streetName || streetName === 'all') return this.globalStats;
        const stats = { total: 0, compliant: 0, compliantBuffer: 0, nonCompliant: 0 };
        this.geoData.features.forEach(feature => {
            if (feature.properties._clean_street === streetName) {
                stats.total++;
                if (feature.properties.Compliance_Status === 'ممتثل') stats.compliant++;
                else if (feature.properties.Compliance_Status === 'ممتثل (تقريبي)') stats.compliantBuffer++;
                else stats.nonCompliant++;
            }
        });
        return stats;
    }

    getMunicipalityStats(muniName) {
        if (!muniName || muniName === 'all') return this.globalStats;
        const stats = { total: 0, compliant: 0, compliantBuffer: 0, nonCompliant: 0 };
        this.geoData.features.forEach(feature => {
            if (feature.properties._clean_municipality === muniName) {
                stats.total++;
                if (feature.properties.Compliance_Status === 'ممتثل') stats.compliant++;
                else if (feature.properties.Compliance_Status === 'ممتثل (تقريبي)') stats.compliantBuffer++;
                else stats.nonCompliant++;
            }
        });
        return stats;
    }

    /**
     * Calculates the Map Bounding Box (Viewport) for a given street
     * so MapLibre can easily 'FlyTo' it.
     */
    getStreetBoundingBox(streetName) {
        return this._getBoundingBox(f => f.properties._clean_street === streetName);
    }

    getMunicipalityBoundingBox(muniName) {
        return this._getBoundingBox(f => f.properties._clean_municipality === muniName);
    }

    _getBoundingBox(filterFn) {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        let found = false;
        this.geoData.features.forEach(feature => {
            if (filterFn(feature)) {
                const coords = this._flattenCoordinates(feature.geometry);
                coords.forEach(coord => {
                    if (coord[0] < minX) minX = coord[0];
                    if (coord[1] < minY) minY = coord[1];
                    if (coord[0] > maxX) maxX = coord[0];
                    if (coord[1] > maxY) maxY = coord[1];
                    found = true;
                });
            }
        });
        return found ? [[minX, minY], [maxX, maxY]] : null;
    }

    /** Helper to extract raw coordinates array based on Geometry Type */
    _flattenCoordinates(geometry) {
        if (!geometry || !geometry.coordinates) return [];
        if (geometry.type === 'Point') return [geometry.coordinates];
        if (geometry.type === 'Polygon') return geometry.coordinates[0];
        if (geometry.type === 'MultiPolygon') {
            let pts = [];
            geometry.coordinates.forEach(poly => poly[0].forEach(pt => pts.push(pt)));
            return pts;
        }
        return [];
    }

    /** Helper to recursively remove Z-Coords (Elevation) from GeoJSON Arrays */
    _stripZCoordinates(coords) {
        if (!Array.isArray(coords)) return;

        // If it's a single coordinate pair/triplet like [x, y, z]
        if (coords.length > 0 && typeof coords[0] === 'number') {
            if (coords.length > 2) {
                // Truncate array to keep only [x, y]
                coords.length = 2;
            }
        } else {
            // Nested arrays (e.g. rings in polygons/multipolygons)
            for (let i = 0; i < coords.length; i++) {
                this._stripZCoordinates(coords[i]);
            }
        }
    }

    /** Returns sorted array of valid street names */
    getAllStreets() {
        return Array.from(this.streetsList).sort();
    }

    /** Returns sorted array of valid municipality names */
    getAllMunicipalities() {
        return Array.from(this.municipalityList).sort();
    }
}
