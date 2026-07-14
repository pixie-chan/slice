"""AudioContext fingerprint noise injection."""

SCRIPT = """
// Add noise to AudioContext to prevent audio fingerprinting
if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
    const AC = window.AudioContext || window.webkitAudioContext;
    const _createAnalyser = AC.prototype.createAnalyser;

    AC.prototype.createAnalyser = function() {
        const analyser = _createAnalyser.call(this);
        const _getFloatFrequencyData = analyser.getFloatFrequencyData;
        analyser.getFloatFrequencyData = function(array) {
            _getFloatFrequencyData.call(this, array);
            // Add tiny noise
            for (let i = 0; i < array.length; i++) {
                array[i] += Math.random() * 0.001;
            }
        };
        return analyser;
    };

    // Spoof destination channel count if needed
    const _getDescriptor = Object.getOwnPropertyDescriptor;
    const origDesc = _getDescriptor(AudioNode.prototype, 'channelCount');
    if (origDesc && origDesc.get) {
        const origGet = origDesc.get;
        Object.defineProperty(AudioNode.prototype, 'channelCount', {
            get: function() {
                const val = origGet.call(this);
                // Only modify for destination nodes (fingerprinting target)
                if (this.constructor.name === 'AudioDestinationNode' && this === this.context.destination) {
                    return 2;  // Standard stereo
                }
                return val;
            },
            configurable: true
        });
    }
}
"""


def get_script(profile: dict = None) -> str:
    return SCRIPT
