// Posts each render quantum of the microphone as one mono Float32Array.
class Capture extends AudioWorkletProcessor {
  process(inputs) {
    const channels = inputs[0];
    if (channels && channels.length && channels[0].length) {
      const mono = new Float32Array(channels[0]);
      for (let c = 1; c < channels.length; c++) {
        for (let i = 0; i < mono.length; i++) mono[i] += channels[c][i];
      }
      if (channels.length > 1) for (let i = 0; i < mono.length; i++) mono[i] /= channels.length;
      this.port.postMessage(mono, [mono.buffer]);
    }
    return true;
  }
}

registerProcessor("capture", Capture);
