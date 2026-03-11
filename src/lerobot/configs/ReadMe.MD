# 采集 offline 数据
## 操作顺序：
## 1. 查端口
lerobot-find-port

## 2. 查摄像头
lerobot-find-cameras

## 3. 修改配置文件后，采集示范数据 env_config_so101.json
### 采集都要成功的 完成后按 s
python -m lerobot.rl.gym_manipulator --config_path src/lerobot/configs/env_config_so101_offline.json

## 4. 确定图像裁剪参数
python -m lerobot.rl.crop_dataset_roi --repo-id lerobot --root data/so101_offline_data_02272321
### 完成后生成新的数据集 data/so101_offline_data_cropped_resized

# 采集奖励分类器数据 
## 第一步【采集】：env_config_so101_classifier.json
python -m lerobot.rl.gym_manipulator --config_path src/lerobot/configs/env_config_so101_classifier.json

### 标注按键说明
按键	事件	含义
s	SUCCESS	标记成功，结束 episode 并保存（reward=1）
Esc	FAILURE	标记失败，结束 episode 并保存（reward=0）
r	RERECORD_EPISODE	重录，丢弃当前 episode
Space	IS_INTERVENTION	切换人类干预模式（RL 训练时用）
所以 Esc 是标注失败并保存，不是重录。想重录要按 r。

采集奖励分类器数据时的操作：

完成任务 → 按 p（保存为成功）
故意失败 → 按 q（保存为失败）
操作失误想重来 → 按 r（丢弃重录）
ctrl+c 退出


## 第二步【训练】：reward_classifier_config_so101.json

lerobot-train --config_path src/lerobot/configs/reward_classifier_config_so101.json

训练完成后，把模型路径填到 train_config_hilserl_so101.json 里：
"reward_classifier": {
  "pretrained_path": "outputs/so101_reward_classifier/checkpoints/last/pretrained_model",
  "success_threshold": 0.7,
  "success_reward": 1.0
}

# RL强化学习
## 把裁剪参数填入 train_config，然后启动训练（两个终端） train_config_hilserl_so101.json
### 学习者 
python -m lerobot.rl.learner --config_path src/lerobot/configs/train_config_hilserl_so101.json
### 演示者
python -m lerobot.rl.actor  --config_path src/lerobot/configs/train_config_hilserl_so101.json

## 继续
### 学习者 
 python -m lerobot.rl.learner --config_path outputs/so101_hilserl_learner_03042115/checkpoints/last/pretrained_model/train_config.json --resume true
### 演示者
python -m lerobot.rl.actor  --config_path outputs/so101_hilserl_learner_03042115/checkpoints/last/pretrained_model/train_config.json --resume true
# 映射
## 规则地址
/etc/udev/rules.d/99-aloha-serial.rules
### 查询序列号命令
udevadm info --name=/dev/ttyACM1 | grep -i serial
## 从臂（右）/dev/am_arm_follower_right
## 从臂（左）/dev/am_arm_follower_left
## 主臂（右）/dev/am_arm_leader_right
## 主臂（左）/dev/am_arm_leader_left
## 从臂摄像头（右）/dev/am_camera_wrist_right
## 从臂摄像头（左）/dev/am_camera_wrist_left
## 摄像头（头）/dev/am_camera_hand_top
### 生效
sudo udevadm control --reload-rules && sudo udevadm trigger

115 前
114 后
165 左
163 右
164 升