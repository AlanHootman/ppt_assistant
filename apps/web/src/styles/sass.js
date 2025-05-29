/**
 * Sass 配置文件 - 使用新的 Sass JavaScript API
 */
import * as sass from 'sass';

export default {
  sassOptions: {
    // 使用新的 JS API 方法
    implementation: sass,
    // 其他 Sass 选项
    indentWidth: 2,
    outputStyle: 'compressed'
  }
}; 