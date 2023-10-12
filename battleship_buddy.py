import sys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QTableWidgetItem,
    QWidget, QTableWidget, QComboBox, QPushButton, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qt6agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class HeatmapWidget(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

        # This is the data you will likely get from your probability map
        # Just an example; you should replace this with your actual data
        data = np.random.rand(10, 10)

        # Create the heatmap using imshow
        self.axes.imshow(data, cmap="hot", interpolation="nearest")

        # You might want to set up the axes labels, title, etc.pip install

class NoScrollComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super(NoScrollComboBox, self).__init__(*args, **kwargs)

    def wheelEvent(self, event):
        # Ignore the wheel event
        event.ignore()

class ControlPanel(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app  # Store the reference to the BattleshipApp instance
        self.init_ui()

    def init_ui(self):
        vbox_layout = QVBoxLayout()

        # Reset button
        self.reset_button = QPushButton("Reset Game")
        self.reset_button.clicked.connect(self.reset_game)
        vbox_layout.addWidget(self.reset_button)

        # Ship checkboxes
        self.ship_checkboxes = {}
        for ship in self.app.SHIP_SIZES.keys():  # Accessing ship types from the BattleshipApp instance
            checkbox = QCheckBox(f"{ship} (Not Sunk)")
            checkbox.setChecked(True)  # Initially, ships are not sunk
            checkbox.stateChanged.connect(self.toggle_ship)
            self.ship_checkboxes[ship] = checkbox
            vbox_layout.addWidget(checkbox)

        # Set the layout
        self.setLayout(vbox_layout)

    def reset_game(self):
        # Reset the ship probability maps
        self.app.ship_probability_maps = {
            ship_type: [[0] * self.app.cols for _ in range(self.app.rows)] for ship_type in self.app.SHIP_SIZES
        }

        # Update probability maps for each ship
        for ship_type in self.app.SHIP_SIZES:
            self.app.battleship_grid.calculate_ship_positions(ship_type)

        # Reset the grid state for each BattleshipGrid instance
        self.app.battleship_grid.reset_grid_state()
        self.app.probability_grid.reset_grid_state()

    def toggle_ship(self, state):
        # Implementation of toggle_ship remains the same
        pass  # Placeholder


class BattleshipGrid(QTableWidget):
    def __init__(self, rows, cols, app):
        super().__init__(rows, cols)
        self.app = app  # Here we store the reference to the BattleshipApp instance
        self.grid_state = [["None"] * cols for _ in range(rows)]  # None, Hit, Miss
        self.init_grid()

    def init_grid(self):
        # Initialize the grid with combo boxes
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                comboBox = NoScrollComboBox()
                comboBox.addItems(["", "Hit", "Miss"])
                comboBox.setStyleSheet("background-color: white;")
                comboBox.currentTextChanged.connect(self.update_grid_state)
                self.setCellWidget(row, col, comboBox)
                self.setColumnWidth(col, 50)

                # Adjust the stylesheet to change the selection color
                comboBox.setStyleSheet("""
                    QComboBox {
                        background-color: white;
                        selection-background-color: white;  /* This is the color of the item when the combobox is active */
                        border: none;
                    }
                    QComboBox QAbstractItemView {
                        selection-background-color: transparent;  /* This is the color of the item in the dropdown */
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                """)
        self.horizontalHeader().setDefaultSectionSize(50)
        self.verticalHeader().setDefaultSectionSize(50)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
    
    def reset_grid_state(self):
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                comboBox = self.cellWidget(row, col)
                comboBox.setCurrentIndex(0)  # Reset to the first item (empty string)
                self.grid_state[row][col] = "None"  # Reset the internal state

    def update_grid_state(self, value):
        sender = self.sender()
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                if self.cellWidget(row, col) == sender:
                    self.grid_state[row][col] = value

                    # Update cell color based on hit or miss
                    if value == "Hit":
                        sender.setStyleSheet("background-color: red;")
                    elif value == "Miss":
                        sender.setStyleSheet("background-color: grey;")
                    else:  # Reset to default (white) if the selection is cleared
                        sender.setStyleSheet("background-color: white;")
                    return

    def calculate_ship_positions(self, ship_type):
        # Ensure valid ship type
        if ship_type not in self.app.SHIP_SIZES:
            raise ValueError(f"Invalid ship type: {ship_type}")

        ship_size = self.app.SHIP_SIZES[ship_type]
        probability_map = self.app.ship_probability_maps[ship_type]  # Get the specific ship's probability map

        # Reset the probability map for this ship type
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                probability_map[row][col] = 0

        # Check each position on the grid
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                # Check horizontal placement
                if col + ship_size <= self.columnCount():
                    if all(self.grid_state[row][c] != "Miss" for c in range(col, col + ship_size)):
                        for c in range(col, col + ship_size):
                            probability_map[row][c] += 1

                # Check vertical placement
                if row + ship_size <= self.rowCount():
                    if all(self.grid_state[r][col] != "Miss" for r in range(row, row + ship_size)):
                        for r in range(row, row + ship_size):
                            probability_map[r][col] += 1

        # The method updates the probability map in place, so no need to return anything


class ProbabilityGrid(QTableWidget):
    def __init__(self, rows, cols, app, parent=None):
        super().__init__(rows, cols, parent)
        self.app = app  # Store the reference to the BattleshipApp instance
        self.init_grid()

    def init_grid(self):
        # Set up the grid
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Make the table read-only
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)  # Disable selection

        # Initialize the grid cells
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = QTableWidgetItem()
                self.setItem(row, col, item)

        self.update_grid()

    def update_grid(self):
        # Calculate the sum of probabilities for each cell
        total_probability_map = [[0] * self.app.cols for _ in range(self.app.rows)]
        for ship_map in self.app.ship_probability_maps.values():
            for row in range(self.app.rows):
                for col in range(self.app.cols):
                    total_probability_map[row][col] += ship_map[row][col]

        # Update the grid cells with the new probabilities
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                item.setText(str(total_probability_map[row][col]))


class BattleshipApp(QMainWindow):
    SHIP_SIZES = {
        "Destroyer": 2,
        "Submarine": 3,
        "Cruiser": 3,
        "Battleship": 4,
        "Carrier": 5,
    }

    def __init__(self, rows=10, cols=10):
        super().__init__()
        self.rows = rows
        self.cols = cols

        # Initialize a separate probability map for each ship type
        self.ship_probability_maps = {
            ship_type: [[0] * self.cols for _ in range(self.rows)] for ship_type in self.SHIP_SIZES
        }
        
        self.init_ui()

        # Update probability maps for each ship
        for ship_type in self.SHIP_SIZES:
            self.battleship_grid.calculate_ship_positions(ship_type)

        # Explicitly update the probability grid after calculating ship positions
        self.probability_grid.update_grid()

    def init_ui(self):
        # Set main window properties
        self.setWindowTitle("Battleship Buddy")
        self.setGeometry(700, 100, 800, 1200)  # Set position and size

        # Set the navy blue background color for the app
        self.setStyleSheet("background-color: #2F4E9E;")
        # Rest of code....
        # Create a central widget to hold our layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a vertical box layout for the widgets
        vbox_layout = QVBoxLayout()

        # Create the interactive battleship grid for hits/misses
        self.battleship_grid = BattleshipGrid(10, 10, self) # Passing the BattleshipApp instance to the BattleshipGrid
        vbox_layout.addWidget(self.battleship_grid)

        # Create the grid for displaying probabilities
        self.probability_grid = ProbabilityGrid(self.rows, self.cols, self)
        # vbox_layout.addWidget(self.probability_grid)

        # Create and add the heatmap widget
        self.heatmap_widget = HeatmapWidget()
        vbox_layout.addWidget(self.heatmap_widget)

        self.print_probability_map = QPushButton("Print Probability Maps")
        self.print_probability_map.clicked.connect(self.print_probability_map_clicked)
        vbox_layout.addWidget(self.print_probability_map)

        # Create the control panel
        self.control_panel = ControlPanel(self)  # Passing the BattleshipApp instance to the ControlPanel
        vbox_layout.addWidget(self.control_panel)

        # Apply the vertical box layout to the central widget
        central_widget.setLayout(vbox_layout)

        # Show the main window
        self.show()

    def print_probability_map_clicked(self):
        print(self.ship_probability_maps)

def main():
    app = QApplication(sys.argv)
    main_win = BattleshipApp()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
