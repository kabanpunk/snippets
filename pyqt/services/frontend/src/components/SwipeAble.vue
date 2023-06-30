
<template>
  <div class="main-container" >
    <div
        class="video-container"
        ref="interactElement"
        :style="{
          transform: transformString,
          transition: transitionString,
          touchAction: 'none'
        }"
    >

      <video class="card" ref="videoElement" width="450" autoplay muted loop :src="video"></video>
    </div>

    <video class="next-frame" width="450" :src="nextFrame"> </video>
    <button v-if="isVideoMuted && showVolumeToggle" class="caption" @click="muteToggleVideo" ><i ref="btnContent" class="bi bi-volume-mute"></i></button>
    <button v-if="!isVideoMuted && showVolumeToggle" class="caption" @click="muteToggleVideo" ><i ref="btnContent" class="bi bi-volume-up"></i></button>

    <div v-if="showHintToggle" class="caption-text-hint">
      <h3>Смахни если видео наскучило</h3>
    </div>
    <svg v-if="showHintToggle" class="caption-hint" id="Swipe-vertical_1" data-name="Swipe vertical 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
      <path class="hand-y" d="M131.09,69.21l-34,24.17-21.6-21.6a9.25,9.25,0,0,0-13.08,0h0a9.25,9.25,0,0,0,0,13.08L103,125.43l-14.18-1.08c-5.11,0-8.72,3.22-9.25,9.25,0,0-1,9.25,3.83,9.25h48l30.14-30.14A9.25,9.25,0,0,0,162.72,101L143.43,72.11A9.28,9.28,0,0,0,131.09,69.21Z"/>
      <g class="swipe-vertical">
        <path class="line-vertical" d="M43.94,94.27c-12.46-19.69,0-37,0-37"/>
        <polyline class="arrow-down" points="47.93 88.53 45.35 96.75 45.33 96.75 37.11 94.17"/>
        <polyline class="arrow-up" points="46.59 64.92 44.01 56.69 43.98 56.7 35.76 59.28"/>
      </g>
    </svg>
  </div>

</template>

<script>
import interact from "interactjs";
import axios from "axios";
import 'bootstrap-icons/font/bootstrap-icons.css'
const INTERACT_ON_START = "start";
const INTERACT_ON_MOVE = "move";
const INTERACT_ON_END = "end";
const SWIPE_LEFT = "swipe-left";
const SWIPE_RIGHT = "swipe-right";
const SWIPE_TOP = "swipe-top";
const SWIPE_BOTTOM = "swipe-bottom";
const SWIPE_ANY = "swipe";

export default {
  name: "SwipeAble",
  props: {
    mode: Boolean,
    video_name: String,
    maxRotation: {
      type: Number,
      default: 15,
      required: false,
    },
    outOfSightXOffset: {
      type: Number,
      default: 1000,
      required: false,
    },
    outOfSightYOffset: {
      type: Number,
      default: 1000,
      required: false,
    },
    thresholdX: {
      type: Number,
      default: 100,
      required: false,
    },
    thresholdY: {
      type: Number,
      default: 120,
      required: false,
    },
  },
  data() {
    return {
      index: 0,
      showVolumeToggle: true,
      showHintToggle: false,
      isVideoMuted: true,
      video:  '',
      nextFrame: '',
      videos: [

      ],
      movingSpeed: 0.7,
      isDragging: true,
      interactPosition: {
        x: 0,
        y: 0,
        rotation: 0,
      },

    };
  },
  computed: {
    transformString() {
      const { x, y, rotation } = this.interactPosition;
      return `translate3D(${x}px, ${y}px, 0) rotate(${rotation}deg)`;
    },
    transitionString() {
      console.log("transitionString: ", this.isDragging, this.movingSpeed);
      return !this.isDragging && "transform "+ this.movingSpeed + "s cubic-bezier(0.2, 0.8, 0.4, 1.2)";
    },
  },
  async mounted() {
    let response = await axios.get('/videos/random-list');
    console.log(response);

    let hint_resp = await axios.get('/users/hint');
    if (this.mode) {
      this.showHintToggle = hint_resp.data;
    }

    let jsons = response.data;
    for (let data in jsons) {
      this.videos.push(axios.defaults.baseURL + 'static/' + jsons[data].name + '.mp4');
      console.log(jsons[data].name)
    }
    this.video = this.videos[this.index];
    this.index = (this.index + 1) % this.videos.length;
    this.nextFrame = this.videos[this.index] + '#t=1';
    const element = this.$refs.interactElement;

    this.$refs.videoElement.addEventListener('loadeddata', this.onload_video, false);

    if (this.mode) {
      interact(element).draggable({
        onstart: () => {
          this.$emit(INTERACT_ON_START);
          this.isDragging = true;
        },
        onmove: (event) => {
          this.$emit(INTERACT_ON_MOVE);
          const { maxRotation, thresholdX } = this.$props;
          const x = this.interactPosition.x + event.dx;
          const y = this.interactPosition.y + event.dy;

          let rotation = maxRotation * (x / thresholdX);
          if (rotation > maxRotation) rotation = maxRotation;
          else if (rotation < -maxRotation) rotation = -maxRotation;
          this.setPosition({ x, y, rotation });
        },
        onend: () => {
          this.$emit(INTERACT_ON_END);
          const { x, y } = this.interactPosition;
          const { thresholdX, thresholdY } = this.$props;
          console.log(x, thresholdX)
          this.isDragging = false;
          if (y < -thresholdY) this.onThresholdReached(SWIPE_TOP);
          else if (y > thresholdY) this.onThresholdReached(SWIPE_BOTTOM);
          else this.setPosition({ x: 0, y: 0, rotation: 0 });
        },
      });
    }
    this.timer = setInterval(() => {
      this.showVolumeToggle = false;
      this.showHintToggle = false;
    }, 5000)
  },
  beforeUnmount() {
    this.unsetInteractElement();
  },
  methods: {
    onload_video() {
      this.setPosition({ x: 0, y: 0, rotation: 0 });
      this.isDragging = true;
      this.nextFrame = this.videos[this.index] + '#t=1';
    },
    get_current_video_name() {
      let current_video_name  = this.video.split("/");
      current_video_name = current_video_name[current_video_name.length - 1].split(".")[0];
      return current_video_name;
    },
    capture() {
      let videoCanvas =  this.$refs.canvasElement;
      let video = this.$refs.videoElement;
      videoCanvas.getContext("2d").drawImage(video, 0, 0, video.videoWidth, video.videoHeight);
    },
    muteToggleVideo() {
      const videoEl = this.$refs.videoElement;
      this.isVideoMuted = !this.isVideoMuted;
      videoEl.muted = this.isVideoMuted;
    },
    getVideoUrl(vid) {
      return require('../assets/'+vid)
    },
    onThresholdReached(interaction) {
      const { outOfSightXOffset, outOfSightYOffset, maxRotation } = this.$props

      let isBackSwipe = false;
      switch (interaction) {
        case SWIPE_RIGHT:
          this.setPosition({
            x: outOfSightXOffset,
            rotation: maxRotation,
          });
          this.$emit(SWIPE_RIGHT);
          break;
        case SWIPE_LEFT:
          this.setPosition({
            x: -outOfSightXOffset,
            rotation: -maxRotation,
          });
          this.$emit(SWIPE_LEFT);
          break;
        case SWIPE_TOP:
          this.setPosition({
            y: -outOfSightYOffset,
          });
          this.$emit(SWIPE_TOP);
          break;
        case SWIPE_BOTTOM:
          this.setPosition({
            y: outOfSightYOffset,
          });
          isBackSwipe = true;
          this.$emit(SWIPE_BOTTOM);
          break;
      }
      this.$emit(SWIPE_ANY, interaction, this.get_current_video_name());
      this.isDragging = false;

      setTimeout(() => {
        this.video = this.videos[this.index];
        this.index = (this.index + 1) % this.videos.length;
      }, 300);

    },
    setPosition(position) {
      const { x = 0, y = 0, rotation = 0 } = position;
      this.interactPosition = { x, y, rotation };
    },
    unsetInteractElement() {
      interact(this.$refs.interactElement).unset();
    },
  },
};
</script>

<style>
.main-container {
  position: relative;
  height: 100%;
  width: 100%;
  border:1px solid;
}
.main-container .video-container {
  z-index: 1;
  object-fit: fill;
  display: inline-block;
  width: 100%;
  height: 100vh;
  background: #FFFFFF;
  border-radius: 50px;
  overflow: hidden;
  position: absolute;
  will-change: transform;
  transition: all 0.3s ease-in-out;
  cursor: grab;
}
.video-container video {
  z-index: 2;
  width: 100%;
  height: 100%;
  position: absolute;
  object-fit: cover;
}
.main-container .caption {
  z-index: 3;
  position: absolute;
  left:  40%;
  right: 40%;
  bottom: 85%;
  top: 5%;
  font-size: xxx-large;
  border-radius: 10px;
   background: rgba(190, 190, 190, 0.5);
  /*background:none;*/
  border:none;
}
.main-container .caption-hint {
  z-index: 3;
  position: absolute;
  left:  30%;
  right: 30%;
  bottom: 30%;
  top: 30%;
  font-size: xxx-large;
  border-radius: 10px;
  border:none;
}
.main-container .caption-text-hint {
  z-index: 3;
  position: absolute;
  left:  5%;
  right: 5%;
  bottom: 40%;
  top: 15%;
  font-size: medium;
  border-radius: 10px;
  border:none;
  text-align: center;
  text-shadow: 1px 0 #fff, -1px 0 #fff, 0 2px #fff, 0 -1px #fff,
  1px 1px #fff, -1px -1px #fff, 1px -1px #fff, -1px 1px #fff;
}
.main-container .next-frame {
  z-index: 0;
  object-fit: cover;
  display: inline-block;
  width: 100%;
  height: 100vh;
  background: #FFFFFF;
  border-radius: 50px;
  overflow: hidden;
  position: absolute;
  will-change: transform;
  transition: all 0.3s ease-in-out;
  cursor: grab;
}
.search-icon {
  background-size: contain;
  cursor: pointer;
  display: inline-block;
  height: 52px;
  width: 40px;
}

.hand,
.hand-double,
.hand-flick,
.hand-hold,
.hand-rock,
.hand-tap,
.hand-x,
.hand-y {
  fill: #fff;
  stroke: #000;
  stroke-width: 3px;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.arrow-down,
.arrow-head,
.arrow-left,
.arrow-right,
.arrow-up,
.arrow-up-1,
.arrow-up-2,
.arrow-up-3,
.hold-1,
.hold-2,
.line-horizontal,
.line-rotate,
.line-vertical,
.notes,
.tap-1,
.tap-2 {
  fill: transparent;
  stroke: #000;
  stroke-width: 3px;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.arrow-up-2,
.hold-1,
.tap-1 {
  opacity: .5;
}

.arrow-up-1,
.hold-2,
.tap-2 {
  opacity: .25;
}

.arrow-up-3,
.swipe-horizontal,
.swipe-rotate,
.swipe-vertical {
  opacity: .75;
}

.hold-1,
.hold-2,
.notes {
  opacity: 0;
}

/* ANIMATION KEYFRAMES */

@keyframes tap-double {
  0% {
    transform: rotateX(0deg);
  }
  10% {
    transform: rotateX(12.5deg);
  }
  25% {
    transform: rotateX(25deg);
  }
  35% {
    transform: rotateX(10deg);
  }
  50% {
    transform: rotateX(25deg);
  }
}

@keyframes tap {
  0% {
    transform: rotateX(0deg);
  }
  10% {
    transform: rotateX(12.5deg);
  }
  25% {
    transform: rotateX(25deg);
  }
}

@keyframes tap-circle {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  75% {
    transform: scale(1.05);
    opacity: .6;
  }
  80% {
    transform: scale(1);
    opacity: .5;
  }
}

@keyframes hold {
  0% {
    transform: rotateX(0deg);
  }
  10% {
    transform: rotateX(12.5deg);
  }
  30% {
    transform: rotateX(25deg);
  }
  80% {
    transform: rotateX(25deg);
  }
}

@keyframes fade {
  0% {
    opacity: 0;
  }
  30% {
    opacity: .75
  }
  80% {
    opacity: .75;
  }
}

@keyframes swipe-x {
  0% {
    transform: translateX(0px);
  }
  25% {
    transform: translateX(50px) rotateZ(10deg);
  }
  50% {
    transform: translateX(0px);
  }
  75% {
    transform: translateX(-50px) rotateZ(-10deg);
  }
}

@keyframes swipe-y {
  0% {
    transform: translateY(0px);
  }
  25% {
    transform: translateY(50px) rotateZ(-10deg);
  }
  50% {
    transform: translateY(0px);
  }
  75% {
    transform: translateY(-50px) rotateZ(10deg);
  }
}

@keyframes flick-fade {
  0% {
    opacity: 0;
  }
  25% {
    opacity: 1;
  }
}

@keyframes flick {
  0% {
    transform: rotateZ(0deg);
  }
  10% {
    transform: translateY(-12px) rotateZ(50deg);
  }
  25% {
    transform: rotateZ(5deg);
  }
}

@keyframes spin {
  0% {
    transform: rotateZ(0deg);
  }
  10% {
    transform: translateY(-10deg) rotateZ(-20deg);
  }
  50% {
    transform: rotateZ(45deg);
  }
}

@keyframes rock-on {
  0% {
    transform: scale(1);
  }
  25% {
    transform: scale(1.1);
  }
  50% {
    transform: scale(1);
  }
  75% {
    transform: scale(1.1);
  }
}

@keyframes note {
  0% {
    transform: scale(0) rotateZ(0deg);
    opacity: 0;
  }
  20% {
    transform: scale(1.1) rotateZ(10deg);
  }
  40% {
    transform: scale(0.9) rotateZ(-10deg);
  }
  50% {
    opacity: .75;
  }
  60% {
    transform: scale(1.1) rotateZ(10deg);
  }
  80% {
    transform: scale(0.9) rotateZ(-10deg);
  }
}

/* SVG ANIMATION */

.wrapper * {
  transform-origin: 50% 50%;
  perspective: 100px;
}

.hand {
  transform-origin: 25% 50%;
}

.hand-tap {
  animation: tap 1.25s ease-out backwards;
  animation-iteration-count:infinite;
}

.hand-double {
  animation: tap-double 1.25s ease-out backwards;
  animation-iteration-count:infinite;
}

.tap-1,
.tap-2 {
  animation: tap-circle 1.25s ease-out backwards;
  animation-iteration-count:infinite;
}

.hand-hold {
  animation: hold 1.25s ease-out backwards;
  animation-iteration-count:infinite;
}

.hold-1, .hold-2 {
  animation: fade 1.25s ease-in backwards;
  animation-iteration-count:infinite;
}

.tap-2 {
  animation-delay: 0.2s;
}

.hand-x {
  animation: swipe-x 1.25s ease-in-out backwards;
  animation-iteration-count:infinite;
}

.hand-y {
  animation: swipe-y 1.25s ease-in-out backwards;
  animation-iteration-count:infinite;
}

.hand-flick {
  animation: flick 1.25s ease-out backwards;
  animation-iteration-count:infinite;
}

.arrows {
  opacity: 0;
  animation: flick-fade 1.25s ease-out backwards;
  animation-iteration-count:infinite;
}

.hand,
.swipe-rotate {
  animation: spin 1.25s ease-in-out backwards;
  animation-iteration-count:infinite;
}

.hand-rock {
  animation: rock-on 1.25s ease-out backwards;
  animation-iteration-count:infinite;
}

.notes {
  animation: note 1.25s ease-out backwards;
  animation-iteration-count:infinite;
}
</style>
