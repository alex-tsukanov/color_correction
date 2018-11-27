import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import QWidget

# TODO: not allow nodes go out of canvas
# TODO: fix center behaviour
from image.image import correct_image


class DragAndDropCanvas(QWidget):
    """Custom canvas (QPainter-like) widget that supports dragging of nodes by mouse"""

    def __init__(self, grid, palette, parent=None, delta=30):
        """delta - minimum distance at which node reacts to mouse dragging\
        (actually square distance).
        Affects grid sensitivity"""
        super().__init__(parent)
        self._delta = delta
        self._palette = palette
        self._grid = grid
        self._parent = parent
        
        self.draggin_idx = None
        self.setGeometry(0, 0, self._grid.radius * 2, self._grid.radius * 2)

        self._pen_pinned = QPen(Qt.black, 10, Qt.SolidLine)
        self._pen_notpinned = QPen(Qt.black, 5, Qt.SolidLine)
        self._pen_edge = QPen(Qt.black, 1, Qt.SolidLine)

        self._update_nodes_array()

    def _update_nodes_array(self):
        """writes numpy array of all grid's nodes to instance field self._nodes"""
        self._nodes = np.array([node.coords_for_canvas for branch in self._grid.branches for node in branch.nodes])
        # nodes are stored as a numpy copy to simplify and fasten calculations of distances

    def paintEvent(self, e):
        painter = QPainter()
        painter.begin(self)
        self._update_nodes_array()  # copy changes of branch update inside this class
        self.draw_points(painter)
        self.draw_edges(painter)
        painter.end()

    def draw_points(self, painter: QPainter):
        for i, (x, y) in enumerate(self._nodes):
            painter.setPen(
                self._pen_pinned if self._grid[i].is_pinned else self._pen_notpinned)
            painter.drawPoint(x, y)

    def draw_edges(self, painter: QPainter):
        painter.setPen(self._pen_edge)

        # radial edges
        for branch in self._grid.branches:
            for from_, to in zip(branch.nodes, branch.nodes[1:]):
                painter.drawLine(*from_.coords_for_canvas, *to.coords_for_canvas)

        # concentric edges
        nodes_per_branch = len(self._grid.branches)
        for i in range(nodes_per_branch):
            for branch_from, branch_to in zip(self._grid.branches, self._grid.branches[1:] + [self._grid.branches[0]]):
                painter.drawLine(
                                *branch_from.nodes[i].coords_for_canvas,
                                *branch_to.nodes[i].coords_for_canvas
                                 )

    def _get_mouse_position(self, evt):
        return np.array([evt.pos().x(), evt.pos().y()])

    def mousePressEvent(self, evt):
        if evt.button() == Qt.LeftButton and self.draggin_idx is None:
            point = self._get_mouse_position(evt)

            def _get_clicked_node_idx():
                # dist will hold the square distance from the click to the points
                dist = self._nodes - point
                dist = dist[:, 0] ** 2 + dist[:, 1] ** 2
                dist[dist > self._delta] = np.inf  # obviate the distances above DELTA
                if dist.min() < np.inf:
                    return dist.argmin()
                else:
                    return None
            self.draggin_idx = _get_clicked_node_idx()

    def _redraw_to_new_mouse_position(self, evt, recalculate_all=False):
        point = self._get_mouse_position(evt)
        self._nodes[self.draggin_idx] = point

        node_to_update = self._grid[self.draggin_idx]

        node_to_update.move_to(*(point - self._grid.radius))
        self._grid.update_grid(recalculate_all)

        self.update()

    def mouseMoveEvent(self, evt):
        if self.draggin_idx is not None:
            self._redraw_to_new_mouse_position(evt)

    def mouseReleaseEvent(self, evt):
        if evt.button() == Qt.LeftButton and self.draggin_idx is not None:
            self._redraw_to_new_mouse_position(evt, recalculate_all=True)
            self.draggin_idx = None
            self._parent.processed = correct_image(self._parent.initial_lab, self._palette, self._grid)

