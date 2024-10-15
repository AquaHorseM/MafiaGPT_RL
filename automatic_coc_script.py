import os
from argparse import ArgumentParser
from automatic_coc_utils import make_battle_dir_and_run_one_battle

def two_battle_war(args):
    make_battle_dir_and_run_one_battle('right_wolf', args.war_folder,
                                       os.path.join(args.left_clan_notes_dir,'villager'),os.path.join(args.left_clan_notes_dir,'seer'),os.path.join(args.left_clan_notes_dir,'medic'),
                                       os.path.join(args.right_clan_notes_dir,'werewolf'),
                                       args.left_clan_tag, args.left_clan_tag, args.left_clan_tag,
                                       args.right_clan_tag,
                                        args.num_games_per_battle, args.num_process)
    make_battle_dir_and_run_one_battle('left_wolf', args.war_folder,
                                        os.path.join(args.right_clan_notes_dir,'villager'),os.path.join(args.right_clan_notes_dir,'seer'),os.path.join(args.right_clan_notes_dir,'medic'),
                                        os.path.join(args.left_clan_notes_dir,'werewolf'),
                                        args.right_clan_tag, args.right_clan_tag, args.right_clan_tag,
                                        args.left_clan_tag,
                                         args.num_games_per_battle, args.num_process)



if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--war_folder', type=str, default = './clan_war_shijz_14_v1Vv9')
    parser.add_argument('--left_clan_notes_dir', type=str, default =  './shijz_test_14/notes/notes_v1')
    parser.add_argument('--right_clan_notes_dir', type=str, default = './shijz_test_14/notes/notes_v9')
    parser.add_argument('--left_clan_tag', type=str, default = 'shijz_test_14_notes_v1')
    parser.add_argument('--right_clan_tag', type=str, default = 'shijz_test_14_notes_v9')
    parser.add_argument('--num_games_per_battle', type=int, default = 5)
    parser.add_argument('--num_process', type=int, default = 5)
    args = parser.parse_args()
    two_battle_war(args)
