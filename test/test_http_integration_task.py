"""
测试HTTP集成任务处理器

测试HTTP集成任务类型在综合处理模块中的功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.task_handlers import task_handlers
from utils.logger import Logger


async def test_http_integration_handler():
    """测试HTTP集成任务处理器"""
    Logger.info("=" * 60)
    Logger.info("开始测试HTTP集成任务处理器")
    Logger.info("=" * 60)

    # 测试1: 基本GET请求（不保存响应）
    Logger.info("\n测试1: 基本GET请求（不保存响应）")
    params1 = {
        "method": "GET",
        "url": "https://httpbin.org/get",
        "query_params": {
            "test": "value",
            "param": "123"
        },
        "save_response": False,
        "task_id": "test1"
    }

    result1 = await task_handlers.get_handler("http_integration")(params1)
    print(f"结果1: {result1}")
    assert result1["success"] == True
    assert result1["status_code"] == 200
    assert "response_body" in result1
    Logger.info("✅ 测试1通过")

    # 测试2: GET请求并保存响应
    Logger.info("\n测试2: GET请求并保存响应")
    params2 = {
        "method": "GET",
        "url": "https://httpbin.org/get",
        "query_params": {
            "test": "save"
        },
        "save_response": True,
        "save_filename": "test_response",
        "task_id": "test2"
    }

    result2 = await task_handlers.get_handler("http_integration")(params2)
    print(f"结果2: {result2}")
    assert result2["success"] == True
    assert result2["status_code"] == 200
    assert "saved_file" in result2
    assert Path(result2["saved_file"]).exists()
    Logger.info(f"✅ 测试2通过，文件已保存: {result2['saved_file']}")

    # 测试3: POST JSON请求
    Logger.info("\n测试3: POST JSON请求")
    params3 = {
        "method": "POST",
        "url": "https://httpbin.org/post",
        "headers": {
            "Content-Type": "application/json"
        },
        "body_json": {
            "name": "test",
            "value": 123,
            "data": ["a", "b", "c"]
        },
        "save_response": True,
        "save_filename": "post_response",
        "task_id": "test3"
    }

    result3 = await task_handlers.get_handler("http_integration")(params3)
    print(f"结果3: {result3}")
    assert result3["success"] == True
    assert result3["status_code"] == 200
    assert "saved_file" in result3
    Logger.info("✅ 测试3通过")

    # 测试4: 带认证的请求
    Logger.info("\n测试4: 带认证的请求")
    params4 = {
        "method": "GET",
        "url": "https://httpbin.org/headers",
        "auth_config": {
            "type": "api_key",
            "key_name": "X-API-Key",
            "key_value": "test-api-key-123"
        },
        "save_response": False,
        "task_id": "test4"
    }

    result4 = await task_handlers.get_handler("http_integration")(params4)
    print(f"结果4: {result4}")
    assert result4["success"] == True
    assert result4["status_code"] == 200
    Logger.info("✅ 测试4通过")

    # 测试5: 带自定义请求头的请求
    Logger.info("\n测试5: 带自定义请求头的请求")
    params5 = {
        "method": "GET",
        "url": "https://httpbin.org/headers",
        "headers": {
            "Custom-Header": "custom-value",
            "Another-Header": "another-value"
        },
        "save_response": False,
        "task_id": "test5"
    }

    result5 = await task_handlers.get_handler("http_integration")(params5)
    print(f"结果5: {result5}")
    assert result5["success"] == True
    assert result5["status_code"] == 200
    Logger.info("✅ 测试5通过")

    # 测试6: POST表单数据
    Logger.info("\n测试6: POST表单数据")
    params6 = {
        "method": "POST",
        "url": "https://httpbin.org/post",
        "form_data": {
            "field1": "value1",
            "field2": "value2"
        },
        "save_response": True,
        "save_filename": "form_response",
        "task_id": "test6"
    }

    result6 = await task_handlers.get_handler("http_integration")(params6)
    print(f"结果6: {result6}")
    assert result6["success"] == True
    assert result6["status_code"] == 200
    Logger.info("✅ 测试6通过")

    # 测试7: 检查任务处理器是否已注册
    Logger.info("\n测试7: 检查任务处理器是否已注册")
    available_handlers = task_handlers.get_available_handlers()
    print(f"可用的任务处理器: {available_handlers}")
    assert "http_integration" in available_handlers
    assert available_handlers["http_integration"] == "HTTP集成"
    Logger.info("✅ 测试7通过")

    Logger.info("\n" + "=" * 60)
    Logger.info("所有测试通过！")
    Logger.info("=" * 60)


async def test_http_integration_with_template():
    """测试HTTP集成在模板中的使用"""
    Logger.info("\n" + "=" * 60)
    Logger.info("开始测试HTTP集成在模板中的使用")
    Logger.info("=" * 60)

    from modules.task_orchestrator import task_orchestrator
    from modules.template_manager import template_manager

    # 加载示例模板（使用模板的name字段作为键）
    template = template_manager.get_template("HTTP集成示例模板")
    if not template:
        Logger.error("模板不存在: HTTP集成示例模板")
        return

    Logger.info(f"模板名称: {template['name']}")
    Logger.info(f"模板描述: {template['description']}")

    # 执行模板
    parameters = {
        "api_url": "https://httpbin.org/get",
        "api_method": "GET",
        "query_param": "template_test",
        "save_response": True
    }

    result = await task_orchestrator.execute_template(
        template_name="HTTP集成示例模板",
        parameters=parameters
    )

    Logger.info(f"模板执行结果: {result}")
    assert result["success"] == True
    assert "task_outputs" in result

    # 检查任务输出
    task1_output = result["task_outputs"].get("task1")
    assert task1_output is not None
    assert task1_output["success"] == True
    assert task1_output["status_code"] == 200

    if "saved_file" in task1_output:
        saved_file = Path(task1_output["saved_file"])
        assert saved_file.exists()
        Logger.info(f"✅ 模板测试通过，文件已保存: {saved_file}")
    else:
        Logger.info("✅ 模板测试通过")

    Logger.info("\n" + "=" * 60)
    Logger.info("模板测试通过！")
    Logger.info("=" * 60)


async def main():
    """主函数"""
    try:
        # 测试HTTP集成任务处理器
        await test_http_integration_handler()

        # 测试HTTP集成在模板中的使用
        await test_http_integration_with_template()

    except Exception as e:
        Logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
