class TmAsmDecoder:
  DEFAULT_ATTACHED_SYNC_MARKER = b'\x1A\xCF\xFC\x1D'
  
  def __init__(self, asm: bytes = DEFAULT_ATTACHED_SYNC_MARKER, strip_asm: bool = True):
    self._asm = asm
    self._strip_asm = strip_asm
    
  def apply(self, data: bytes) -> bytes:
    if not data.startswith(self._asm):
      raise ValueError("ASM not found at the beginning of the data")
    return data[len(self._asm):] if self._strip_asm else data
  
  def __call__(self, data: bytes) -> bytes:
    return self.apply(data)
