# ComfyUI 工作流目录

此目录用于存放 ComfyUI 工作流 JSON 文件，这些文件可以通过文件名直接调用。

## 使用方法

### 1. 工作流文件格式

工作流文件应为标准的 ComfyUI 工作流 JSON 格式。

### 2. 参数替换

在工作流 JSON 中，可以使用 `{{参数名}}` 格式定义可替换的参数。

例如：
```json
{
  "1": {
    "inputs": {
      "text": "{{prompt}}",
      "width": {{width}},
      "height": {{height}}
    },
    "class_type": "SomeNode"
  }
}
```

### 3. 参数替换规则

- 字符串参数：使用双花括号包裹，如 `{{prompt}}`
- 数字参数：直接使用双花括号，如 `{{width}}`
- 布尔参数：使用双花括号，如 `{{enabled}}`
- 嵌套参数：支持点号表示法，如 `{{model.name}}`

### 4. 示例工作流

当前目录包含以下示例工作流：

- `example_text_to_image.json` - 文本生成图像示例工作流

### 5. 调用方式

#### 通过 UI 调用

1. 选择工作流文件
2. 输入参数（JSON 格式）
3. 执行工作流

#### 通过 API 调用

```bash
POST /api/comfyui/execute_from_file

请求参数：
- workflow_file: 工作流文件名（如 "example_text_to_image.json"）
- params: 参数 JSON（可选）
- server_url: ComfyUI 服务器地址
- auth_token: 认证 Token（可选）
- username: 用户名（可选）
- password: 密码（可选）
- timeout: 超时时间（秒）
```

### 6. 参数示例

对于 `example_text_to_image.json` 工作流，可以传入以下参数：

```json
{
  "prompt": "a beautiful sunset over the ocean",
  "seed": 123456,
  "model_name": "v1-5-pruned-emaonly.safetensors",
  "width": 512,
  "height": 512,
  "output_prefix": "my_image"
}
```

## 注意事项

1. 确保工作流 JSON 格式正确
2. 参数名称必须与工作流中定义的参数名一致
3. 参数类型必须匹配（字符串、数字、布尔等）
4. 如果参数未提供，将保留原始值