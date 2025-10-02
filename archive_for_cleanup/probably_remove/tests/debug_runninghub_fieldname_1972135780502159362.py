import uuid
import json
from datetime import datetime

import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from app import create_app, db
from app.models.Task import Task
from app.models.TaskData import TaskData
from app.services.runninghub import RunningHubService

"""
目的：
- 复用远程任务ID 1972135780502159362 对应的本地 Task/TaskData 作为提示词基础
- 将节点 51 的字段从默认的 "video" 改为 RunningHub 工作流要求的 "file" 和 "video-preview"
- 将节点 36 的字段设置为 "image"
- 使用本地文件：
  - 视频：/Users/winston/Desktop/Gitlab/repository/tk/tktool_byclaude/test/doc/黑帽男+1&2.mp4
  - 图片：/Users/winston/Desktop/Gitlab/repository/tk/tktool_byclaude/test/doc/模特图.png
- 运行一次测试任务，输出新远程 taskId 以及关键节点的参数预览

注意：
- 为了让 RunningHubService 的日志写入不过外键约束，先创建一个测试 Task 记录，然后将其 task_id 传给 run_task
"""

VIDEO_PATH = "/Users/winston/Desktop/Gitlab/repository/tk/tktool_byclaude/test/doc/黑帽男+1&2.mp4"
IMAGE_PATH = "/Users/winston/Desktop/Gitlab/repository/tk/tktool_byclaude/test/doc/模特图.png"
TARGET_RUNNINGHUB_TASK_ID = "1972135780502159362"


def build_node_info_list(base_data, video_file_name, image_file_name):
    """在原始 TaskData 基础上，覆盖节点 51 和 36 的字段"""
    node_info_list = []

    # 先复制原始数据
    for d in base_data:
        node_info_list.append({
            "nodeId": d.node_id,
            "fieldName": d.field_name,
            "fieldValue": d.field_value,
        })

    # 删除节点 51 的旧字段（例如 "video"），并加入 "file" 与 "video-preview"
    node_info_list = [n for n in node_info_list if not (n["nodeId"] == "51" and n["fieldName"] in ("video", "file", "video-preview"))]
    node_info_list.append({"nodeId": "51", "fieldName": "file", "fieldValue": video_file_name})
    node_info_list.append({"nodeId": "51", "fieldName": "video-preview", "fieldValue": ""})

    # 节点 36 设置为 "image"
    node_info_list = [n for n in node_info_list if not (n["nodeId"] == "36" and n["fieldName"] in ("image", "video"))]
    node_info_list.append({"nodeId": "36", "fieldName": "image", "fieldValue": image_file_name})

    return node_info_list


def main():
    app = create_app()
    with app.app_context():
        service = RunningHubService()

        # 查找本地 Task（通过远程ID）
        target_task = Task.query.filter_by(runninghub_task_id=TARGET_RUNNINGHUB_TASK_ID).first()
        if not target_task:
            print(f"未找到 runninghub_task_id={TARGET_RUNNINGHUB_TASK_ID} 对应的本地任务，请确认数据库记录。")
            return

        # 读取原始 TaskData 作为提示词基础
        base_data = TaskData.query.filter_by(task_id=target_task.task_id).all()
        if not base_data:
            print("目标任务没有 TaskData 记录，无法复用提示词。")
            return

        # 创建一个新的测试 Task 以满足日志外键约束
        test_task_id = f"TEST-{TARGET_RUNNINGHUB_TASK_ID}-{str(uuid.uuid4())[:8]}"
        test_task = Task(
            task_id=test_task_id,
            workflow_id=target_task.workflow_id,
            status="READY",
            task_description=f"Debug fieldName for nodes 51/36 based on {TARGET_RUNNINGHUB_TASK_ID}",
            is_plus=target_task.is_plus,
        )
        db.session.add(test_task)
        db.session.commit()

        # 上传视频
        try:
            with open(VIDEO_PATH, "rb") as vf:
                video_bytes = vf.read()
            video_file_name = service.upload_file(video_bytes, VIDEO_PATH.split("/")[-1], task_id=test_task_id)
        except Exception as e:
            print(f"视频上传失败: {e}")
            return

        # 上传图片
        try:
            with open(IMAGE_PATH, "rb") as imf:
                image_bytes = imf.read()
            image_file_name = service.upload_file(image_bytes, IMAGE_PATH.split("/")[-1], task_id=test_task_id)
        except Exception as e:
            print(f"图片上传失败: {e}")
            return

        # 构建 nodeInfoList，覆盖节点 51 和 36
        node_info_list = build_node_info_list(base_data, video_file_name, image_file_name)

        print("即将调用 run_task，关键节点参数预览：")
        for n in node_info_list:
            if n["nodeId"] in ("51", "36"):
                print(json.dumps(n, ensure_ascii=False))

        # 调用 RunningHub 执行
        try:
            new_runninghub_task_id = service.run_task(
                node_info_list=node_info_list,
                task_id=test_task_id,
                workflow_id=target_task.workflow_id,
                is_plus=bool(target_task.is_plus),
            )
            test_task.runninghub_task_id = new_runninghub_task_id
            test_task.status = "RUNNING"
            db.session.commit()
            print(f"新任务已发起，runninghub_task_id={new_runninghub_task_id}")
        except Exception as e:
            print(f"任务发起失败: {e}")
            return

        # 简单轮询状态（最多 10 次，每次 5 秒）
        import time
        for i in range(10):
            status = service.get_status(new_runninghub_task_id, test_task_id)
            print(f"状态轮询[{i+1}/10]: {status}")
            if status and status.upper() in ("SUCCESS", "FAILED"):
                break
            time.sleep(5)

        print("调试完成。请在数据库 logs 表中查看详细调用日志。")


if __name__ == "__main__":
    main()