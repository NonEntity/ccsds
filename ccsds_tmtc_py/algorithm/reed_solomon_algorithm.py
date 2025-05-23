import reedsolo # type: ignore
 # Add 'type: ignore' if type checkers complain about reedsolo module if it has no stubs

class ReedSolomonAlgorithm:
  def __init__(self, nsym: int, fcr: int = 0, prim: int = 0x11d, c_exp: int = 8, k_val: int = -1):
    self.nsym = nsym
    self.fcr = fcr
    self.prim = prim
    self.c_exp = c_exp
    self.n = (2**self.c_exp) - 1
    self.k = k_val if k_val != -1 else self.n - self.nsym
    # Allow k to be specified for non-standard n,k combinations if lib supports it,
    # otherwise default to n - nsym. For (255,223), nsym=32, k=223.
    if self.k + self.nsym != self.n and k_val != -1:
        # This case is for when n is not 2**c_exp - 1, e.g. shortened codes.
        # The reedsolo library handles this by taking nsym, and n, k are implicit from data length or full codeword length.
        # For a pure CCSDS (255,223) or (255,X) code, n=255.
        # Let's ensure N and K are consistent with nsym for the standard case.
        pass # For non-standard n,k, the library might handle it if data has k symbols.
            
    try:
      self.rs = reedsolo.RSCodec(self.nsym, nsize=self.n, fcr=self.fcr, prim=self.prim, c_exp=self.c_exp)
    except TypeError as e:
        # Older versions of reedsolo might not have nsize, c_exp in constructor
        # Try a simpler constructor if the full one fails
        print(f"Warning: Full RSCodec constructor failed ({e}). Trying compatibility constructor.")
        self.rs = reedsolo.RSCodec(self.nsym, fcr=self.fcr, prim=self.prim)


  @staticmethod
  def create_tm_reed_solomon_255_223(interleave_depth: int = 1) -> 'ReedSolomonAlgorithm':
    if interleave_depth != 1:
      print(f"Warning: ReedSolomonAlgorithm interleave_depth={interleave_depth} > 1. " \
                    f"This instance handles a single (255,223) block. Interleaving must be managed externally.")
    return ReedSolomonAlgorithm(nsym=32, fcr=112, prim=0x11D, c_exp=8, k_val=223) # CCSDS uses 0x11D as per Blue Book for TM

  def encode(self, data_block: bytes) -> bytes:
    if len(data_block) != self.k:
      raise ValueError(f"Input data length {len(data_block)} for encode does not match K={self.k}")
    return self.rs.encode(data_block) # Returns message + ecc (N bytes total)

  def decode(self, codeword: bytes) -> bytes:
    if len(codeword) != self.n:
      raise ValueError(f"Codeword length {len(codeword)} for decode does not match N={self.n}")
    try:
        # reedsolo.decode returns the full corrected message (N bytes)
        # The library's behavior for RScodec.decode(bytes) is typically to return a bytearray of the repaired message+ecc.
        decoded_full_codeword = self.rs.decode(codeword) 
        # The decode method of RSCodec returns a tuple (decoded_msg, decoded_msgecc, errata_pos)
        # where decoded_msg is K bytes, decoded_msgecc is N bytes.
        # We need to return only the K data bytes.
        # If it's already K bytes, it means an option was set (e.g. no_ecc=True on decode call, not used here)
        # The task implies we get N bytes back and slice.
        # Let's check the type of decoded_full_codeword.
        # If it's a tuple, we want the first element (message part).
        # If it's a bytearray/bytes and N long, we slice.
        if isinstance(decoded_full_codeword, tuple):
            # (message, message_with_ecc, errata_locations) or similar based on version
            # Assuming the first element is the K-byte data portion.
            # Or, if the task implies that "decoded_full_codeword" is the N-byte block, then slice.
            # The common use of `rs.decode(bytearray)` returns the N-byte corrected message.
            # Example: `rsc = RSCodec(10); encoded = rsc.encode(bytearray(range(15))); decoded = rsc.decode(encoded);`
            # Here `decoded` is a bytearray of N bytes.
             return bytes(decoded_full_codeword[0][:self.k]) # If it returns (msg_k_bytes, msg_n_bytes, err_loc)
        elif isinstance(decoded_full_codeword, (bytes, bytearray)):
             if len(decoded_full_codeword) == self.n:
                return bytes(decoded_full_codeword[:self.k])
             elif len(decoded_full_codeword) == self.k: # Some versions might return K bytes directly
                return bytes(decoded_full_codeword)
             else:
                raise ValueError(f"Unexpected decode output length: {len(decoded_full_codeword)}")
        else:
            raise TypeError(f"Unexpected type from reedsolo.decode: {type(decoded_full_codeword)}")

    except reedsolo.ReedSolomonError as e:
      raise ValueError(f"Reed-Solomon: Uncorrectable error during decode: {e}")
    except Exception as e:
      raise ValueError(f"Reed-Solomon: Error during decode: {e}")

if __name__ == '__main__':
    # Test TM R-S (255,223)
    rs_tm = ReedSolomonAlgorithm.create_tm_reed_solomon_255_223()
    print(f"TM R-S: N={rs_tm.n}, K={rs_tm.k}, CheckSymbols={rs_tm.nsym}") # Use .n and .k
    assert rs_tm.n == 255
    assert rs_tm.k == 223
    assert rs_tm.nsym == 32
    assert rs_tm.prim == 0x11D 
    assert rs_tm.fcr == 112

    # Test encode
    data_k = bytes(range(rs_tm.k))
    encoded_n = rs_tm.encode(data_k)
    print(f"Encoded length: {len(encoded_n)}")
    assert len(encoded_n) == rs_tm.n
    assert encoded_n[0:rs_tm.k] == data_k 
    # Check symbols are not all zeros (with a real RS lib)
    assert encoded_n[rs_tm.k:] != bytes(rs_tm.nsym), "Check symbols should not be all zeros with real RS"
    print("Encode test PASSED.")

    # Test decode
    decoded_k = rs_tm.decode(encoded_n)
    print(f"Decoded length: {len(decoded_k)}")
    assert len(decoded_k) == rs_tm.k
    assert decoded_k == data_k
    print("Decode test PASSED.")

    print("ReedSolomonAlgorithm (real library) tests completed.")
