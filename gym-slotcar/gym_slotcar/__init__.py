from gym.envs.registration import register

register(
    id='slotcar-v0',
    entry_point='gym_slotcar.envs:SlotcarEnv',
)
