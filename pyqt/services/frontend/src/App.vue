<template>
  <div id="app">
    <SwipeAble
        v-if="isMounted" v-on:swipe="onSwipe" :mode="mode"
    />
  </div>
</template>

<script>

import SwipeAble from './components/SwipeAble.vue'

import axios from "axios"

export default {
  name: "App",
  components: { SwipeAble },
  data() {
    return {
      isMounted: false,
      mode: false,
    };
  },
  async mounted() {
    let urlParams = new URLSearchParams(window.location.search);

    if (!urlParams.has('uai') || !urlParams.has('token') || !urlParams.has('mode')) {
      alert("The required URL parameters are missing")
      return;
    }

    this.mode = (urlParams.get('mode') === 'true');

    await axios.post('users/', {
      token: urlParams.get('token'),
      uai: urlParams.get('uai'),
      lat: (urlParams.has('lat')) ? urlParams.get('lat') : 0,
      lon: (urlParams.has('lon')) ? urlParams.get('lon') : 0,
    });

    await axios.post('users/create_session/' + urlParams.get('uai'));
    await axios.get('users/whoami');
    this.isMounted = true;
  },
  methods: {
    async onSwipe(direction, video_name) {

      let direction_id = 1;

      switch (direction) {
        case 'swipe-top':
          direction_id = 1;
          break;
        case 'swipe-bottom':
          direction_id = 2;
          break;
        case 'swipe-left':
          direction_id = 3;
          break;
        case 'swipe-right':
          direction_id = 4;
          break;
      }

      await axios.post('users/choice/?video_name='+video_name+'&dir=' + direction_id);
    },
  },
};
</script>

<style>
body {
  margin: 0;
}

#app {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  width: 100vw;
}
</style>
