import click
import json
import math
import pathlib

from lxml import etree

__version__ = "0.1.0"

def parse_blueprint(blueprint: pathlib.Path) -> dict[str, int]:
	"""
	"""
	tree = etree.parse(str(blueprint))
	root = tree.getroot()
	grids = root.find("ShipBlueprints/ShipBlueprint/CubeGrids")
	
	res = dict()
	
	for g in grids:
		blocks = g.find("CubeBlocks")
		for b in blocks:
			k = b.find("SubtypeName").text
			if k is None:
				# Hacks for blocks not obeying the usual structure
				type_id = b.get("{http://www.w3.org/2001/XMLSchema-instance}type") # Accesses the xsi:type
				if type_id == "MyObjectBuilder_OxygenTank":
					k = "LargeOxygenTank"
				elif type_id == "MyObjectBuilder_OxygenGenerator":
					k = "OxygenGenerator"
				elif type_id == "MyObjectBuilder_AirVent":
					k = "AirVent"
				elif type_id == "MyObjectBuilder_GravityGenerator":
					k = "GravityGenerator"
				else:
					raise Exception(f"Found unidentifyable block without proper subtype. Entity ID: {b.find('EntityId').text}")
			if k not in res:
				res[k] = 0
			res[k] += 1
	return res

def parse_block_set_file(filepath: pathlib.Path):
	"""
	"""
	tree = etree.parse(str(filepath))
	root = tree.getroot()
	blocks = root.findall("CubeBlocks/Definition")
	
	res = dict()
	
	for b in blocks:
		name = b.find("Id/SubtypeId").text
		if name is None:
			# Dirty hacks because the game files don't use their structure consistently
			type_id = b.find("Id/TypeId").text
			gridsize = b.find("CubeSize").text
			if type_id == "OxygenTank" and gridsize == "Large":
				name = "LargeOxygenTank"
			elif type_id in ["AirVent", "GravityGenerator", "OxygenGenerator"]:
				name = type_id
		current = {
			"build_time": 0,
			"components": dict()
		}
		components = b.find("Components")
		for c in components:
			if c.get("Count") is not None:
				k = c.get("Subtype")
				if k not in current["components"]:
					current["components"][k] = 0
				current["components"][k] += int(c.get("Count"))
		build_time = b.find("BuildTimeSeconds")
		if build_time is not None:
			current["build_time"] = float(build_time.text)
		res[name] = current
	return res

def parse_items_file(filepath: pathlib.Path):
	"""
	"""
	tree = etree.parse(str(filepath))
	root = tree.getroot()
	items = root.findall("Blueprints/Blueprint")
	
	def get_name_proper(element):
		"""
		Includes ore and ingot to the name of the element
		"""
		t = element.get("TypeId")
		n = element.get("SubtypeId")
		if t == "Ore":
			return f"{n} Ore"
		elif t == "Ingot":
			return f"{n} Ingot"
		else:
			return n
	
	res = dict()
	
	for i in items:
		tmp = i.find("Result")
		sub_id = i.find("Id/SubtypeId").text
		if tmp is None:
			r = i.find("Results")
			if len(r) == 1:
				tmp = r.getchildren()[0]
			else:
				continue
		
		# Ugly hack to fix ugly hacks being used in the game
		if sub_id in ["IceToOxygen", "HydrogenBottlesRefill", "OxygenBottlesRefill", "ScrapIngotToIronIngot", "ScrapToIronIngot"]:
			continue
		name = get_name_proper(tmp)
		
		current = {
			"ingredients": dict(),
			"quantity": float(tmp.get("Amount")),
			"build_time": float(i.find("BaseProductionTimeInSeconds").text)
		}
		for p in i.find("Prerequisites"):
			current["ingredients"][get_name_proper(p)] = float(p.get("Amount"))
		res[name] = current
	return res

def build_database(steamapps_folder):
	"""
	"""
	data_folder = pathlib.Path(steamapps_folder) / "common/SpaceEngineers/Content/Data"
	block_data_folder = data_folder / "CubeBlocks"
	
	if not data_folder.exists():
		return False, dict()
	
	block_db = dict()
	
	for file in block_data_folder.rglob("*.sbc"):
		block_db |= parse_block_set_file(file)
	
	item_db = parse_items_file(data_folder / "Blueprints.sbc")
	
	res = {
		"blocks": block_db,
		"items": item_db
	}
	
	return True, res

def load_database():
	"""
	"""
	res = None
	try:
		with open("components_db.json", 'r') as f:
			res = json.load(f)
	except:
		return False, dict()
	
	return True, res

def save_database(data):
	with open("components_db.json", 'w') as f:
		json.dump(data, f, indent = '\t')

def format_time(seconds: int) -> str:
	"""
	"""
	seconds = int(math.ceil(seconds))
	
	days = seconds // 86400
	seconds = seconds - days * 86400
	hours = seconds // 3600
	seconds = seconds - hours * 3600
	minutes = seconds // 60
	seconds = seconds - minutes * 60
	return f"{days:>3} days, {hours:02}:{minutes:02}:{seconds:02}"

@click.command()
@click.version_option(version = __version__)
@click.argument("blueprint", type = str, required = True)
@click.option("-s", "--steamapps_folder", type = str, default = "C:\\Program Files (x86)\\Steam\\steamapps", help = "Steamapps directory containing the Space Engineers installation.", show_default = True)
@click.option("-r", "--rebuild", type = bool, is_flag = True, default = False, help = "Rebuilds component cost database from game files.", show_default = True)
def main(blueprint, steamapps_folder, rebuild) -> None:
	"""
	"""
	
	from_cache = False
	
	if rebuild:
		success, cost_db = build_database(steamapps_folder)
		if not success:
			print(f"ERROR: No valid Space Engineers installation found in {steamapps_folder}. Please set the correct install directory with the -s option.")
			return
	else:
		success, cost_db = load_database()
		if not success:
			print("INFO: Component database cache not found, rebuilding.")
			success, cost_db = build_database(steamapps_folder)
			if not success:
				print("ERROR: Failed to build component database.")
				print(f"ERROR: No valid Space Engineers installation found in {steamapps_folder}. Please set the correct install directory with the -s option.")
				return
		else:
			from_cache = True
	
	blocks_needed = parse_blueprint(blueprint)
	
	# Sanity check
	if from_cache:
		try:
			a = None
			for block, _ in blocks_needed.items():
				a = cost_db["blocks"][block]
		except:
			print("INFO: Found a block in the blueprint not found in the cached database. Attempting to rebuild.")
			success, cost_db = build_database(steamapps_folder)
			if not success:
				print(f"ERROR: No valid Space Engineers installation found in {steamapps_folder}. Please set the correct install directory with the -s option.")
				return
			else:
				print("INFO: Rebuilt the database from game files.")
	
	save_database(cost_db)
	
	components_needed = dict()
	ingots_needed = dict()
	ores_needed = dict()
	
	total_build_time = 0
	total_craft_time = 0
	total_smelt_time = 0
	
	for block, quantity in blocks_needed.items():
		total_build_time += cost_db["blocks"][block]["build_time"] * quantity
		for component, count in cost_db["blocks"][block]["components"].items():
			if component not in components_needed:
				components_needed[component] = 0
			components_needed[component] += count * quantity

	for component, quantity in components_needed.items():
		if component != "ZoneChip":
			total_craft_time += cost_db["items"][component]["build_time"] * quantity
		for ingot, ingot_quantity in cost_db["items"][component]["ingredients"].items():
			if ingot not in ingots_needed:
				ingots_needed[ingot] = 0
			ingots_needed[ingot] += ingot_quantity * quantity
	
	for ingot, quantity in ingots_needed.items():
		production_quantity = cost_db["items"][ingot]["quantity"]
		if ingot != "ZoneChip":
			total_smelt_time += cost_db["items"][ingot]["build_time"] * quantity
		for ore, ore_quantity in cost_db["items"][ingot]["ingredients"].items():
			if ore not in ores_needed:
				ores_needed[ore] = 0
			ores_needed[ore] += ore_quantity * quantity / production_quantity

	print("Total components required:")
	for component, quantity in sorted(components_needed.items()):
		print(f"{component:30}: {quantity:20.1f}")
	
	print("")
	print("Total ingots needed:")
	for ingot, quantity in sorted(ingots_needed.items()):
		print(f"{ingot:30}: {quantity:20.1f}")
	
	print("")
	print("Total ores needed:")
	for ore, quantity in sorted(ores_needed.items()):
		print(f"{ore:30}: {quantity:20.1f}")

	total_time = total_build_time + total_craft_time + total_smelt_time
	
	ratio_build = round(100 * total_build_time / total_time, 1)
	ratio_craft = round(100 * total_craft_time / total_time, 1)
	ratio_smelt = round(100 * total_smelt_time / total_time, 1)

	print("")
	print("Total time needed to build entire blueprint from scratch (ores):")
	print(f"Building: {format_time(total_build_time)} ({ratio_build:5.1f} %)")
	print(f"Crafting: {format_time(total_craft_time)} ({ratio_craft:5.1f} %)")
	print(f"Smelting: {format_time(total_smelt_time)} ({ratio_smelt:5.1f} %)")
	print(f"Total: {format_time(total_time)}")

if (__name__ == "__main__"):
	main()
