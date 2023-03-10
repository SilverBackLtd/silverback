from ape import Contract, chain

from silverback import SilverBackApp

app = SilverBackApp()
YFI = Contract("0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e")


@app.start()
def start():
    return {"message": "Starting..."}


@app.exec(chain.blocks)
def exec_block(block):
    return {"block_number": block.number}


@app.exec(YFI.Transfer)
def exec_log_event1(log):
    return {**log.event_arguments}


@app.exec(YFI.Approval)
def exec_log_event2(log):
    return {**log.event_arguments}


@app.stop()
def stop():
    return {"message": "Stopping..."}
