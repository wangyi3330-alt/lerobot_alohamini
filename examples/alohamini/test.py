import time, sys
sys.path.insert(0, 'src')                                              
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors import Motor, MotorNormMode

bus = FeetechMotorsBus(port='/dev/am_arm_follower_left', motors={
      'shoulder_pan': Motor(1, 'sts3215', MotorNormMode.DEGREES),
      'shoulder_lift': Motor(2, 'sts3215', MotorNormMode.DEGREES),
      'elbow_flex': Motor(3, 'sts3215', MotorNormMode.DEGREES),
      'wrist_flex': Motor(4, 'sts3215', MotorNormMode.DEGREES),
      'wrist_roll': Motor(5, 'sts3215', MotorNormMode.DEGREES),
      'gripper': Motor(6, 'sts3215', MotorNormMode.RANGE_0_100),
  })
bus.connect()
pos = bus.sync_read('Present_Position')
times_r, times_w = [], []
for i in range(30):
      t = time.perf_counter()
      bus.sync_read('Present_Position')
      times_r.append((time.perf_counter()-t)*1000)
      t = time.perf_counter()
      bus.sync_write('Goal_Position', pos)
      times_w.append((time.perf_counter()-t)*1000)
bus.disconnect()
print(f'sync_read  avg:{sum(times_r)/len(times_r):.1f}msmax:{max(times_r):.1f}ms')
print(f'sync_write avg:{sum(times_w)/len(times_w):.1f}msmax:{max(times_w):.1f}ms')