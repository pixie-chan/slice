"""Canvas fingerprint noise injection."""

SCRIPT = """
;(function() {
const _toDataURL = HTMLCanvasElement.prototype.toDataURL;
const _toBlob = HTMLCanvasElement.prototype.toBlob;
const _getImageData = CanvasRenderingContext2D.prototype.getImageData;

// Per-session noise seed — consistent within a session, unique across sessions
const _CANVAS_SEED = Math.floor(Math.random() * 1000000);

function _addNoise(imageData) {
    const data = imageData.data;
    for (let i = 0; i < data.length; i += 4) {
        const noise = ((i * _CANVAS_SEED + _CANVAS_SEED) % 5) - 2;
        data[i] = Math.max(0, Math.min(255, data[i] + noise));
        data[i+1] = Math.max(0, Math.min(255, data[i+1] + noise));
        data[i+2] = Math.max(0, Math.min(255, data[i+2] + noise));
    }
    return imageData;
}

HTMLCanvasElement.prototype.toDataURL = function() {
    const ctx = this.getContext('2d');
    if (ctx && this.width > 0 && this.height > 0) {
        const imageData = _getImageData.call(ctx, 0, 0, this.width, this.height);
        _addNoise(imageData);
        ctx.putImageData(imageData, 0, 0);
    }
    return _toDataURL.apply(this, arguments);
};

HTMLCanvasElement.prototype.toBlob = function(callback) {
    const ctx = this.getContext('2d');
    if (ctx && this.width > 0 && this.height > 0) {
        const imageData = _getImageData.call(ctx, 0, 0, this.width, this.height);
        _addNoise(imageData);
        ctx.putImageData(imageData, 0, 0);
    }
    return _toBlob.call(this, callback);
};

CanvasRenderingContext2D.prototype.getImageData = function() {
    const imageData = _getImageData.apply(this, arguments);
    _addNoise(imageData);
    return imageData;
};
})();
"""


def get_script(profile: dict = None) -> str:
    return SCRIPT
