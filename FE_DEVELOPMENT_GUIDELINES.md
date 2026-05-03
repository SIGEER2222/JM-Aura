# 前端开发规范

## 0. 紧急修复清单

### 0.1 文件编码问题
- **问题现象**: 页面显示乱码（中文显示为 `????` 或方块字符）
- **原因**: 文件编码被错误修改为 GBK 或其他编码
- **修复方法**:
  ```bash
  # 检查并修复编码
  python -c "
  import os
  filepath = 'frontend/views/config.html'
  with open(filepath, 'rb') as f:
      content = f.read()
  content_str = content.decode('gbk')
  with open(filepath, 'w', encoding='utf-8') as f:
      f.write(content_str)
  print('Fixed:', filepath)
  "
  ```

## 1. 开发环境检查

### 1.1 浏览器控制台检查
- **必须**在开发过程中定期检查浏览器控制台（F12）
- **必须**修复所有 JavaScript 错误（红色错误提示）
- **建议**关注警告信息（黄色提示），尽可能修复

### 1.2 Vue 开发注意事项
- **禁止**在 Vue 模板表达式中换行，这会导致编译错误
  - 错误示例：
    ```html
    {{ isDark ? 'Dark Mode' : 'Light 
        Mode' }}  <!-- 错误：表达式不能换行 -->
    ```
  - 正确示例：
    ```html
    {{ isDark ? 'Dark Mode' : 'Light Mode' }}  <!-- 正确：表达式在同一行 -->
    ```

## 2. 文件编码规范

### 2.1 编码标准
- **所有前端文件**必须使用 **UTF-8 编码**（无 BOM）
- **禁止**使用 GBK、GB2312 等其他编码

### 2.2 编码检查
- 修改文件后应验证编码是否保持 UTF-8
- 使用以下命令批量检查编码：
  ```bash
  python -c "
  import os
  for root, dirs, files in os.walk('frontend'):
      for f in files:
          if f.endswith('.html') or f.endswith('.js'):
              filepath = os.path.join(root, f)
              try:
                  with open(filepath, 'r', encoding='utf-8') as f:
                      f.read()
              except UnicodeDecodeError:
                  print(f'ERROR: {filepath} is not UTF-8')
  "
  ```

### 2.3 编码问题原因
- 某些编辑器（如记事本）在保存时可能自动转换为 GBK
- 复制粘贴操作可能导致编码变化
- 建议使用 VS Code 并设置默认编码为 UTF-8

## 3. 代码规范

### 3.1 命名规范
- 变量/函数名：使用 camelCase
- 组件名：使用 PascalCase
- 常量：使用 UPPER_SNAKE_CASE

### 3.2 Vue 组件规范
- 组件模板应保持简洁
- 复杂逻辑应提取到 methods 或 computed 中
- 避免在模板中写过于复杂的表达式

## 4. 调试技巧

### 4.1 常用调试方法
1. `console.log()` - 输出变量值
2. `debugger` 语句 - 设置断点
3. Vue DevTools - 检查组件状态

### 4.2 API 调试
- 使用浏览器网络面板检查 API 请求/响应
- 确认返回数据格式符合预期

## 5. 性能优化

### 5.1 基本优化
- 避免不必要的重渲染
- 使用 v-if/v-show 合理控制元素显示
- 列表渲染使用 :key

### 5.2 资源优化
- 图片按需加载
- 避免大文件阻塞加载

## 6. 代码审查清单

在提交代码前，请检查：
- [ ] 浏览器控制台无错误
- [ ] 代码格式符合规范
- [ ] 变量命名清晰
- [ ] 注释充分（复杂逻辑）
- [ ] 无未使用的变量/导入
- [ ] 性能考虑周全

---

*文档版本: 1.0*
*最后更新: 2026-05-03*
