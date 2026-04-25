import csv
from pathlib import Path

from torchvision import datasets


def export_split(dataset, split_name: str, out_root: Path, labels_rows: list[list[str]]) -> int:
	written = 0
	class_counters = {i: 0 for i in range(10)}

	for image, label in dataset:
		label = int(label)
		class_name = str(label)
		class_dir = out_root / class_name
		class_dir.mkdir(parents=True, exist_ok=True)

		class_counters[label] += 1
		filename = f"{split_name}_{class_counters[label]:05d}.png"
		rel_path = f"{class_name}/{filename}"
		image.save(class_dir / filename)

		labels_rows.append([rel_path, class_name])
		written += 1

	return written


def write_description(out_root: Path, total_samples: int, split_counts: dict[str, int]) -> None:
	lines = [
		"Data were taken from the MNIST collection.",
		"",
		f"{total_samples} labeled samples",
		"",
		"Images of different main classes are organised into different subfolders.",
		"",
		"-------------------------------",
		"CLASS_NAME\t#LABELED_IMAGES",
		"-------------------------------",
	]

	per_class_counts = {str(i): 0 for i in range(10)}
	labels_csv = out_root / "labels.csv"
	with labels_csv.open("r", newline="") as f:
		reader = csv.reader(f)
		for row in reader:
			per_class_counts[row[1]] += 1

	for class_name in sorted(per_class_counts.keys(), key=int):
		lines.append(f"{class_name}\t\t{per_class_counts[class_name]}")

	lines.extend(
		[
			"",
			f"TOTAL\t\t{total_samples}",
			"",
			"Each labeled image is paired with one label in labels.csv:",
			"relative_path,class_name",
			"",
			"Splits included:",
			f"train={split_counts['train']}",
			f"test={split_counts['test']}",
		]
	)

	(out_root / "description.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
	project_root = Path(__file__).resolve().parents[2]
	out_root = project_root / "data" / "mnist_parsed"
	out_root.mkdir(parents=True, exist_ok=True)

	train_dataset = datasets.MNIST(root=str(project_root / "data"), train=True, download=True)
	test_dataset = datasets.MNIST(root=str(project_root / "data"), train=False, download=True)

	labels_rows: list[list[str]] = []
	split_counts = {
		"train": export_split(train_dataset, "train", out_root, labels_rows),
		"test": export_split(test_dataset, "test", out_root, labels_rows),
	}

	labels_rows.sort(key=lambda r: (int(r[1]), r[0]))
	with (out_root / "labels.csv").open("w", newline="") as f:
		writer = csv.writer(f)
		writer.writerows(labels_rows)

	write_description(out_root, len(labels_rows), split_counts)

	print(f"Created dataset in: {out_root}")
	print(f"Total samples: {len(labels_rows)}")


if __name__ == "__main__":
	main()
