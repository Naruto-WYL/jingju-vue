<template>
  <div class="face-cloud-note">
    <h3>脸谱词云说明</h3>
    <p>三张脸谱分别对应武生忠义、旦角情感、净丑公案三类叙事意象。词语大小表示主题热度，位置贴合脸谱轮廓。</p>
  </div>
</template>

<style scoped>
.face-cloud-note {
  display: grid;
  place-content: center;
  height: 100%;
  padding: 18px;
  color: #5d5046;
  text-align: center;
}

.face-cloud-note h3,
.face-cloud-note p {
  margin: 0;
}

.face-cloud-note h3 {
  margin-bottom: 8px;
  color: #273b58;
  font-size: 16px;
}

.face-cloud-note p {
  font-size: 12px;
  line-height: 1.7;
}
</style>
