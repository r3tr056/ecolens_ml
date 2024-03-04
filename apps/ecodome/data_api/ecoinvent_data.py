
from brightway2 import projects, databases, bw2setup, SingleOutputEcospold2Importer, get_activity, Method, LCA

from functools import lru_cache
from multiprocessing import Process

import tqdm
import logging
import bw2data

class EcoinventSearch:
    def __init__(self, project_name, ecoinvent_path) -> None:
        projects.set_current(project_name)
        if "ecoinvent" not in databases:
            logging.info("Loading ecoinvent database. This may take some time...")
            # Use SQLite3 as the database backend
            bw2setup(database_type="sqlite", dbname="ecoinvent.sqlite")
            ei = SingleOutputEcospold2Importer(ecoinvent_path, "ecoinvent")

            # Use tqdm to monitor database write progress
            num_processes = len(ei.data)
            with tqdm(total=num_processes, desc="Importing ecoinvent", unit="process") as pbar:
                ei.apply_strategies()
                ei.statistics()
                ei.write_database(progress=pbar)

    @lru_cache(maxsize=None)
    def get_activity_by_key(self, key):
        return get_activity(key)

    def search_processes(self, search_string):
        search_results = bw2data.search(search_string)
        return search_results

    def calculate_carbon_footprint(self, process_key):
        activity = self.get_activity_by_key(process_key)
        lca = LCA({activity: 1}, method=('IPCC 2013', 'climate change', 'GWP 100a'))
        # Run the LCA calculation
        lca.lci()
        lca.lcia()

        carbon_footprint = lca.score
        return carbon_footprint

    def calculate_impact(self, process):
        activity = self.get_activity_by_key(process)

        lca = LCA({activity: 1}, method=('IPCC 2013', 'climate change', 'GWP 100a'))
        # Run the LCA calculation
        lca.lci()
        lca.lcia()

        # Sort the processes
        hostspots = sorted(lca.inventory.items(), key=lambda x: x[1], reverse=True)
        co2_hotspots = {}
        for i, (key, value) in enumerate(hostspots[:5]):
            co2_hotspots[key] = {
                "name": key[1],
                "contribution": value
            }

        daly_method = Method(("ReCiPe Midpoint (H)", "human health", "DALY"))
        fep_method = Method(("ReCiPe Midpoint (H)", "freshwater eutrophication", "FEP"))
        land_occ_method = Method(("ReCiPe Midpoint (H)", "land use", "land occupation"))
        water_method = Method(("ReCiPe Midpoint (H)", "water use", "water consumption"))

        result = {
            "gwp_score": lca.score,
            "daly_score": activity.calculate(daly_method),
            "fep_score": activity.calculate(fep_method),
            "land_occ_score": activity.calculate(land_occ_method),
            "water_score": activity.calculate(water_method),
            "co2_hotspots": co2_hotspots,
        }

        return result