# AmmoOS Image 1.0 — field research rewrite (G16 field_opt)
def my_signal_handler (event):
  if (isinstance(event, gdb.SignalEvent)):
    gdb.write("Eeeeeeeeeeeek: in-build AmmoOS Image crashed!\n")
    gdb.execute('info threads')
    gdb.execute("thread apply all backtrace full")

gdb.events.stop.connect(my_signal_handler)
gdb.execute("run")
