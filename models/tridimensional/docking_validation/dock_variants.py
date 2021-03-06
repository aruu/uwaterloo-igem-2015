import argparse
import datetime
import os
from time import time

from rosetta import *

from results_csv import results_to_csv


# variations to account for
dna_nts = "acgt"
programs = ["Chimera", "3DNA"]


def write_dock_stats(score_directory, filename, dock_stats, time_diff):
    """Writes separate files for each variant
    Notes:
    - score_directory has the form results/timestamped folder/
    - dock stats has the form: [dna_init, dna_final, fa_init, fa_final]
    - 'a' appends in case of accidental duplication
    - scores and times are passed in explicitly for argument clarity
    """
    path = os.path.join(score_directory, filename)
    f = open(path, 'a')
    f.write("Initial DNA score: %8.3f\n" % dock_stats[0])
    f.write("Final DNA Score: %8.3f\n" % dock_stats[1])
    f.write("Initial FA score: %8.3f\n" % dock_stats[2])
    f.write("Final FA score: %8.3f\n" % dock_stats[3])
    f.write("Total variant time: %8.3f\n" % time_diff)
    f.close()
    return


def dock_simple(pose):
    """Coarse docking of a pose representing a PAM / program variant
    Returns:
        list of scores in the form [dna_init, dna_final, fa_init, fa_final]
    Notes:
    - docking optimizes for DNA score, which is weighted differently than "Full Atom" (FA) score
    - dna score from demo/D110_DNA_interface.py
    Potential Bugs:
    - setup_foldtree(...) crashes on some systems/configurations
    - docking.set_partners(...) may not be needed
    - use default foldtree (foldtree from pdb) for now
    """
    # specify scoring functions
    fa_score = get_fa_scorefxn()
    dna_score = create_score_function('dna')
    dna_score.set_weight(fa_elec, 1)

    # specify docking protocol
    docking = DockMCMProtocol()
    docking.set_scorefxn(dna_score)
    docking.set_scorefxn_pack(fa_score)
    docking.set_partners("B_ACD")

    # obtain initial and final scores after docking
    dna_init = dna_score(pose)
    fa_init = fa_score(pose)
    docking.apply(pose)
    dna_final = dna_score(pose)
    fa_final = fa_score(pose)
    
    return [dna_init, dna_final, fa_init, fa_final]


def dock_complex(pose):
    """Complex docking of a pose representing a PAM / program variant
    Returns:
        list of scores in the form [dna_init, dna_final, fa_init, fa_final]
    Notes:
    - not implemented
    """
    raise exception("Complex docking not implemented")


def dock_variants(pam_variants, path_to_scores, path_to_pdbs='', complex_docking_flag=False):
    """Docks and scores 2 pdbs for each PAM variant (one for each nt program) using simple docking
    Args:
        pam_variants: list of integers (any from 0 to 63 without repeats) which map to pam strings
        path_to_scores: path to the subdirectory of "results" where the variants are stored
        path_to_pdbs: [default: current directory] path to location of chimera/3DNA folders of PAM variants
        complex_docking_flag: [default: False] if True, use complex dock function (NOT IMPLEMENTED)
    Notes:
    - creates a text file (e.g. 'results_agg_Chimera.txt') for each variant
    - path to variants is typically root/results/<timestamped folder>/<variants>
    - assumes current directory is the root of a folder that contains pdbs in Chimera and 3DNA directories
    """
    for i in pam_variants:
        variant = dna_nts[i / 16] + dna_nts[i / 4 % 4] + dna_nts[i % 4]
        for program in programs:
            print "Running for variant: %s_%s" % (variant, program)
            pdb_path = os.path.join(path_to_pdbs, program, "4UN3." + variant + ".pdb")
            # track runtime while loading and passing pose to the simple docker
            time_init = time()
            loaded_pose = pose_from_pdb(pdb_path)
            if complex_docking_flag:
                dock_complex(loaded_pose)
            else:
                dock_stats = dock_simple(loaded_pose)
            time_final = time()
            # write results to file
            results_filename = variant + "_" + program + ".txt"
            write_dock_stats(path_to_scores, results_filename, dock_stats, time_final - time_init)
            print "Finished writing scores for variant: %s_%s" % (variant, program)
    return


if __name__ == '__main__':
    # create parser and parse arguments
    parser = argparse.ArgumentParser(description='Run docking and scoring on PAM variants')
    parser.add_argument('-s', '--start', metavar='N', type=int,
                        help='starting PAM number (0 = aaa), inclusive')
    parser.add_argument('-e', '--end', metavar='N', type=int,
                        help='ending PAM number (63 = ttt), inclusive')
    parser.add_argument('-o', '--output_dir', metavar='D', type=str,
                        help='path to output directory for variant scores')
    parser.add_argument('--pdb_dir', metavar='D', default='', type=str,
                        help='path to root of variant pdb directories (default: "")')
    parser.add_argument('--complex', metavar='B', nargs='?', const=True, default=False,
                        type=str, help='[switch] select complex docking (default: "False")')
    parser.add_argument('--csv', metavar='B', nargs='?', const=True, default=False,
                        type=str, help='[switch] compile scores to csv (default: "False")')
    args = parser.parse_args()
    
    # setup range of pam variants   
    assert 0 <= args.start <= args.end <= 63
    pam_variants_to_score = range(args.start, args.end + 1)

    # setup output path for scoring
    if args.output_dir is not None:
        path_to_scores = args.output_dir
    else:
        results_folder = "results"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %I.%M.%S%p")
        path_to_scores = "results" + os.sep + timestamp + os.sep
    if not os.path.exists(path_to_scores):
        os.makedirs(path_to_scores)
    
    # initialize pyrosetta and score variants
    init(extra_options="-mute all")  # reduce rosetta print calls
    dock_variants(pam_variants_to_score, path_to_scores, path_to_pdbs=args.pdb_dir, complex_docking_flag=args.complex)

    # collect score txt files into a csv
    if args.csv:
        results_to_csv(path_to_scores)
