// Leaflet choropleth: zips shaded by decile of the selected metric.
/* global L */

const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas';
const TILES = {
  light: `${ESRI}/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
  dark: `${ESRI}/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
};
const LABELS = {
  light: `${ESRI}/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}`,
  dark: `${ESRI}/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}`,
};
const ATTRIBUTION = 'Basemap &copy; <a href="https://www.esri.com">Esri</a>, HERE, Garmin, &copy; OpenStreetMap contributors';

export function createMap(el, geo, { onHover, onSelect }) {
  const map = L.map(el, { zoomControl: true, attributionControl: true, minZoom: 9, maxZoom: 16, zoomSnap: 0.25 });
  map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
  map.createPane('labels');
  map.getPane('labels').style.zIndex = 450;
  map.getPane('labels').style.pointerEvents = 'none';

  let base, labels, theme;
  let style = () => ({});
  let ranked = null;
  let hovered = null;
  let selected = null;

  const layer = L.geoJSON(geo.geojson, {
    style: (f) => style(f),
    onEachFeature: (f, lyr) => {
      lyr.on({
        mouseover: () => onHover(f.properties.zip, true),
        mouseout: () => onHover(f.properties.zip, false),
        click: () => onSelect(f.properties.zip),
      });
    },
  }).addTo(map);

  const byZip = new Map();
  layer.eachLayer((lyr) => byZip.set(lyr.feature.properties.zip, lyr));

  function setTheme(next) {
    if (next === theme) return;
    theme = next;
    base?.remove();
    labels?.remove();
    base = L.tileLayer(TILES[theme], { attribution: ATTRIBUTION, maxNativeZoom: 16 }).addTo(map);
    labels = L.tileLayer(LABELS[theme], { pane: 'labels', maxNativeZoom: 16 }).addTo(map);
  }

  function restyle() {
    layer.setStyle(style);
    if (hovered) byZip.get(hovered)?.bringToFront();
    if (selected) byZip.get(selected)?.bringToFront();
  }

  return {
    map,
    setTheme,
    // colors: { ramp: [10 colors], empty, outline, highlight }
    update({ ranking, inScope, colors, tooltip }) {
      ranked = ranking;
      style = (f) => {
        const zip = f.properties.zip;
        const r = ranked.byZip.get(zip);
        const active = inScope(f);
        const emphasis = zip === hovered || zip === selected;
        return {
          fillColor: r ? colors.ramp[r.decile - 1] : colors.empty,
          fillOpacity: !active ? 0 : r ? 0.85 : 0.35,
          color: emphasis ? colors.highlight : colors.outline,
          weight: emphasis ? 2.5 : active ? 0.6 : 0.3,
          opacity: active ? 1 : 0.4,
        };
      };
      layer.eachLayer((lyr) => {
        const f = lyr.feature;
        if (inScope(f)) lyr.bindTooltip(() => tooltip(f.properties.zip), { sticky: true, className: 'map-tip', direction: 'top', offset: [0, -8] });
        else lyr.unbindTooltip();
      });
      restyle();
    },
    highlight(zip, on) {
      hovered = on ? zip : hovered === zip ? null : hovered;
      restyle();
    },
    select(zip, { fly = true } = {}) {
      selected = zip;
      restyle();
      if (fly && zip && byZip.get(zip)) {
        const b = byZip.get(zip).getBounds();
        if (!map.getBounds().contains(b)) map.flyToBounds(b, { maxZoom: 13, duration: 0.6 });
      }
    },
    fit(features) {
      const fc = { type: 'FeatureCollection', features };
      map.fitBounds(L.geoJSON(fc).getBounds(), { padding: [12, 12] });
    },
    invalidate: () => map.invalidateSize(),
  };
}
