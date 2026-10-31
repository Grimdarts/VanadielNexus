"""A reference view of the exact control labels exported by the active job Lua."""
import json
import os
import time
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QFrame, QVBoxLayout
from .. import widgets
from .base import Page


class G13Page(Page):
    title = 'G13 controls'
    key = 'g13'

    def __init__(self, ctx):
        super().__init__(ctx)
        self.layer = QComboBox()
        self.layer.addItems(['Follow last G-key', 'M1', 'M2', 'M3'])
        self.layout_.addLayout(widgets.hbox(widgets.label('G13 layout', 'SectionTitle'), self.layer, None))
        self.state_label = widgets.label('', 'Caption')
        self.layout_.addWidget(self.state_label)
        self.mode_label=widgets.label('', 'Caption')
        self.mode_label.setTextFormat(Qt.PlainText)
        self.layout_.addWidget(self.mode_label)
        grid = QGridLayout()
        self.labels = []
        for i in range(22):
            row,col = (0,i) if i<7 else (1,i-7) if i<14 else (2,i-14) if i<19 else (3,i-19)
            cell=QFrame()
            cell.setObjectName('Card')
            layout=QVBoxLayout(cell)
            layout.addWidget(widgets.label(f'G{i+1}', 'Caption'))
            label=widgets.label('—')
            label.setTextFormat(Qt.PlainText)
            label.setWordWrap(True)
            label.setMinimumHeight(52)
            layout.addWidget(label)
            grid.addWidget(cell,row,col)
            self.labels.append(label)
        self.layout_.addLayout(grid)
        self.note=widgets.label('M1/M2/M3 follows the last G-key, or the M-buttons once the G13-M-buttons.lua Logitech script is in your profile. Thumb controls remain in your Logitech profile.', 'Caption')
        self.note.setWordWrap(True)
        self.layout_.addWidget(self.note)
        self.layout_.addStretch()
        self.layer.currentIndexChanged.connect(self.refresh)
        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def refresh(self, *_):
        path=os.path.join(self.ctx.windower_dir,'addons','GearSwap','data','Nova-controls-live.json')
        try:
            if os.path.getsize(path)>65536:
                raise ValueError('oversized state')
            with open(path,encoding='utf-8') as source:
                state=json.load(source)
            age=time.time()-float(state['updated_at'])
            if age>6 or age < -5:
                raise ValueError('stale state')
            bank=self.layer.currentText() if self.layer.currentIndex() else state['layer']
            keys=state['keys'][bank]
            self.state_label.setText(f"{state['character']} · {state['job']} · {bank} · live job definitions")
            self.mode_label.setText('\n'.join(str(line) for line in state.get('modes', [])))
            for index,label in enumerate(self.labels):
                label.setText(str(keys[index]))
        except (OSError,ValueError,KeyError,TypeError,IndexError):
            self.state_label.setText('Waiting for live Nova GearSwap controls. Load a configured job in FFXI; stale labels are cleared.')
            self.mode_label.clear()
            for label in self.labels:
                label.setText('—')
