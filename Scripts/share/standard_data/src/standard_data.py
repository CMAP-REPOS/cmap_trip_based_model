"""Share standard model data.

This script prepares standard datasets from a trip-based model run for
sharing. Arguments are read from ../hand/config.yaml.

This script requires the `emme-plus` Python environment and the
`tbmtools` local Python package.

This file can also be imported as a module and contains the following
functions:

    * load_config - loads values from configuration files
    * export - exports standard data files from the trip-based model
    * compress - compresses standard data files into ZIP archives
    * document - renders a HTML data user guide
    * main - the main function of this script
"""

from pathlib import Path
import sys
import os
import logging
import shutil
import multiprocessing

from tqdm import tqdm
import yaml
from jinja2 import Environment, FileSystemLoader
import markdown

sys.path.append(str(Path(__file__).resolve().parents[3]))
import tbmtools.project as tbm
from tbmtools.results import vehicle_trips
from tbmtools.results import trip_roster
from tbmtools.results import person_trips
from tbmtools.results import skims
from tbmtools.results import transit_network
from tbmtools.results import highway_network
from tbmtools.results import sharing

# Path anchors.
src_dir = Path(__file__).resolve().parent
proj_dir = src_dir.parents[3]
out_dir = src_dir.parent.joinpath('output')


def load_config():
    """Load values from configuration files.

    Reads configuration settings from Database/batch_file.yaml and
    ../hand/config.yaml.

    Returns
    -------
    dict of str: any
        Configuration properties as keys and configuration property
        values as values.
    """
    with open(proj_dir.joinpath('Database/batch_file.yaml')) as f:
        batch_file_config = yaml.safe_load(f)
    with open(src_dir.parent.joinpath('hand/config.yaml')) as f:
        config = yaml.safe_load(f)
    config['scenario_code'] = batch_file_config['scenario_code']
    config['model_version'] = batch_file_config['model_version']
    return config

def export(project_file_name, trip_roster_file_name, tg_data_file_name, scenario_code):
    """Export standard data files from the trip-based model.

    Outputs text log file export.log.

    Parameters
    ----------
    project_file_name : str
        Name of source Emme project file (.emp).
    trip_roster_file_name : str
        Name of output trip roster file.
    tg_data_file_name : str
        Name of output trip generation data file.
    scenario_code : int
        Project scenario code.

    Returns
    -------
    dict of str: Path
        Output file name configuration properties as keys and paths to
        locations of exported data files as values.
    """
    # Make output directory.
    out_dir.mkdir(exist_ok=True)
    # Set up log file.
    logging.basicConfig(filename=out_dir.joinpath('export.log'),
                        filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    
    print(f'Writing output to {out_dir}')

    # Start Modeller in the Emme project.
    modeller = tbm.connect(proj_dir.joinpath(project_file_name))
    logging.info(f'Connected to {modeller.desktop.project_file_name()}')
    # Display a progress bar while exporting data.
    export_paths = dict()
    with tqdm(desc='Exporting data', total=11) as pbar:
        # Export vehicle trips from emmebank.
        logging.info('Exporting vehicle trips')
        trip_tables_path = vehicle_trips.export_matrices(out_dir, modeller)
        export_paths['trip_tables'] = trip_tables_path
        pbar.update()
        # Export skims from emmebank.
        logging.info('Exporting skims')
        skims.flag_transit_disconnects(modeller)
        skim_matrices_path = skims.export_matrices(out_dir, modeller)
        export_paths['skim_matrices'] = skim_matrices_path
        pbar.update()
        # Export trip roster from parquet files.
        logging.info('Exporting trip roster')
        trip_roster_path = trip_roster.export(proj_dir, out_dir, trip_roster_file_name)
        export_paths['trip_roster'] = trip_roster_path
        pbar.update()
        # Export auto person trips from trip roster and transit person trips
        # from emmebank.
        logging.info('Exporting person trips')
        trip_tables_path, hov_trip_tables_path = person_trips.export_auto_matrices(proj_dir, out_dir, trip_roster_path)
        export_paths['hov_trip_tables'] = hov_trip_tables_path
        pbar.update()
        person_trips.export_transit_matrices(out_dir, modeller)
        pbar.update()
        # Export peak (AM peak) and off-peak (midday) transit network,
        # itineraries, and attributes as Emme transaction files and
        # shapefiles.
        logging.info('Exporting transit network')
        transit_networks_path = transit_network.export(out_dir,
                                                       scenario=int(scenario_code),
                                                       format='transaction',
                                                       modeller=modeller,
                                                       emmebank=modeller.emmebank)
        export_paths['transit_networks'] = transit_networks_path
        pbar.update()
        peak_transit_network_path, offpeak_transit_network_path = transit_network.export(out_dir,
                                                                                         scenario=int(scenario_code),
                                                                                         format='shape',
                                                                                         modeller=modeller,
                                                                                         emmebank=modeller.emmebank)
        export_paths['peak_transit_network'] = peak_transit_network_path
        export_paths['offpeak_transit_network'] = offpeak_transit_network_path
        pbar.update() 
        # Export each time of day highway network and attributes as Emme
        # transaction files.
        logging.info('Exporting highway network')
        highway_networks_path = highway_network.export_by_tod(out_dir,
                                                              scenario=int(scenario_code),
                                                              format='transaction',
                                                              modeller=modeller,
                                                              emmebank=modeller.emmebank)
        export_paths['highway_networks'] = highway_networks_path
        pbar.update()
        # Export peak highway networks and attributes as shapefiles.
        am_peak_highway_network_path, pm_peak_highway_network_path = highway_network.export_by_tod(out_dir,
                                                                                                   scenario=int(scenario_code),
                                                                                                   format='shape',
                                                                                                   modeller=modeller,
                                                                                                   emmebank=modeller.emmebank,
                                                                                                   period=[3, 7])
        export_paths['am_peak_highway_network'] = am_peak_highway_network_path
        export_paths['pm_peak_highway_network'] = pm_peak_highway_network_path
        pbar.update()
        # Export daily highway network and attributes as Emme transaction
        # files and shapefiles.
        highway_network.export_daily(out_dir,
                                     scenario=int(scenario_code),
                                     format='transaction',
                                     modeller=modeller,
                                     emmebank=modeller.emmebank)
        pbar.update()
        daily_highway_network_path = highway_network.export_daily(out_dir,
                                                                  scenario=int(scenario_code),
                                                                  format='shape',
                                                                  modeller=modeller,
                                                                  emmebank=modeller.emmebank)
        export_paths['daily_highway_network'] = daily_highway_network_path
        pbar.update()
    # Copy TG results to output directory.
    logging.info('Copying TG results')
    tg_dir = proj_dir.joinpath('Database/tg')
    file = sorted(tg_dir.joinpath('data').glob('tg_results*.csv'))[0]
    shutil.copy(file, out_dir)
    file_copy = out_dir.joinpath(file.name)
    renamed_copy = file_copy.with_name(tg_data_file_name)
    if renamed_copy.exists(): 
        os.remove(renamed_copy)
    file_copy.rename(renamed_copy)
    export_paths['tg_data'] = renamed_copy
    # Copy productions and attractions to output subdirectory.
    logging.info('Copying productions and attractions')
    files = [tg_dir.joinpath('fortran/TRIP49_PA_OUT.TXT'),
             tg_dir.joinpath('fortran/TRIP49_PA_WFH_OUT.TXT')]
    pa_tables_path = out_dir.joinpath('prods_attrs')
    pa_tables_path.mkdir(exist_ok=True)
    for file in files:
        shutil.copy(file, pa_tables_path)
    export_paths['pa_tables'] = pa_tables_path
    logging.info('Finished.')
    return export_paths

def compress(zip_file_names, source_paths):
    """ Compress standard data files into ZIP archives.

    Outputs text log file compress.log.

    Parameters
    ----------
    zip_file_names : dict
        Names of compressed data files.
    source_paths : dict of str: Path
        Output file name configuration properties as keys and paths to
        locations of data files to compress as values.
    """
    # Set up log file.
    logging.basicConfig(filename=out_dir.joinpath('compress.log'),
                        filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    
    print(f'Writing compressed output to {out_dir}')

    mp_compress_args = list()
    for placeholder, file_name in zip_file_names.items():
        mp_compress_args.append((file_name, source_paths[placeholder], out_dir))
    # Compress model data for sharing.
    logging.info('Compressing outputs')
    with multiprocessing.Pool() as pool:
        # Display a progress bar while processing the tasks.
        for i in tqdm(iterable=pool.imap_unordered(func=sharing.mp_compress,
                                                   iterable=mp_compress_args),
                      total=len(mp_compress_args),
                      desc='Compressing outputs'):
            pass
    logging.info('Finished.')

def document(context):
    """ Render a HTML data user guide.

    Reads Markdown template with placeholder variables from
    ../hand/data_user_guide_md.txt and HTML template from
    ../hand/data_user_guide_html.txt.

    Parameters
    ----------
    context : dict of str: str
        Configuration properties as keys with text to render as values.
    """
    # Load the Markdown template for data user guide.
    environment = Environment(loader=FileSystemLoader(src_dir.parent.joinpath('hand')))
    md_template = environment.get_template('data_user_guide_md.txt')
    # Render the Markdown template.
    md_file = out_dir.joinpath('data_user_guide.md')
    with open(md_file, mode='w', encoding='utf-8') as file:
        file.write(md_template.render(context))
    # Read Markdown from file.
    with open(md_file, encoding='utf-8') as file:
        md = file.read()
    # Convert Markdown to HTML.
    html = markdown.markdown(text=md, extensions=['tables'])
    # Load the HTML template for data user guide.
    html_template_file = src_dir.parent.joinpath('hand/data_user_guide_html.txt')
    with open(html_template_file, encoding='utf-8') as file:
        html_template = file.read()
    # Render the HTML template.
    with open(md_file.with_suffix('.html'), mode='w', encoding='utf-8') as file:
        file.write(html_template.replace('{{content}}', html))

def main():
    # Load configuration settings.
    config = load_config()
    # Tag for file names.
    tag = f'_{config["title"]}_{config["scenario_code"]}'
    # Export data files.
    tagged_trip_roster_file_name = config['trip_roster'] + tag
    tagged_tg_data_file_name = config['tg_data'] + tag
    export_paths = export(config['project_file_name'],
                          tagged_trip_roster_file_name + '.csv',
                          tagged_tg_data_file_name + '.csv',
                          config['scenario_code'])
    export_paths['tod_transit_networks'] = Path(config['transit_directory'],
                                                str(config['scenario_code']))
    export_paths['database'] = proj_dir.joinpath('Database/emmebank')
    export_paths['matrices'] = proj_dir.joinpath('Database/emmemat')
    # Compress data files.
    zip_file_names = {}
    for placeholder, file_name in config['compressed'].items():
        tagged_file_name = file_name + tag
        zip_file_names[placeholder] = tagged_file_name + '.zip'
    compress(zip_file_names, source_paths=export_paths)
    # Render the data user guide.
    config.update(config.pop('compressed'))
    document(context=config)


if __name__ == '__main__':
    sys.exit(main())