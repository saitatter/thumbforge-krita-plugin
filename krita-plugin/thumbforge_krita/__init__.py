from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita

from .dock import ThumbforgeDocker


Krita.instance().addDockWidgetFactory(
    DockWidgetFactory(
        "thumbforge_krita_docker",
        DockWidgetFactoryBase.DockRight,
        ThumbforgeDocker,
    )
)
