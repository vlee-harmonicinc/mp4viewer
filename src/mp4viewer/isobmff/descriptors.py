"""Defines descriptors from various mpeg-4 standards"""

# pylint: disable=too-many-instance-attributes

from mp4viewer.tree import Tree, TreeType


class BaseDescriptor:
    """
    Base class for all descriptors.
    The size does not include the bytes used to encode the tag and the size.
    """

    def __init__(self, buf):
        self.size = 0
        self.tag = 0
        self.header_size = 1
        self.start_position = buf.current_position()
        self.descriptors = []
        self.parse(buf)
        consumed_bytes = self.consumed_bytes(buf)
        self.unhandled_bytes = None
        # only tag and size were read, capture remaining bytes
        if consumed_bytes == self.header_size:
            self.unhandled_bytes = buf.readbytes(self.size)
            return

        self.parse_unhandled_descriptors(buf)

    def parse(self, buf):
        """
        parse the descriptor from the buffer.
        Subclasses shall override this function and call this super variant before starting
        the descriptor specific parsing.
        """
        self.tag = buf.readbyte()
        self.parse_size(buf)

    def parse_size(self, buf):
        """
        Parse the size of an expandable descriptor.
        See sizeOfInstance in 14496-1 section 8.3.3.
        """
        size = 0
        while True:
            b = buf.readbyte()
            self.header_size += 1
            size = (size << 7) | (b & 0x7F)
            if (b & 0x80) == 0:
                self.size = size
                return

    def parse_unhandled_descriptors(self, buf):
        """
        Take care of any unhandled/optional descriptors at the end of a descriptor body.
        Called from BaseDescriptor.init, so the subclasses don't have to worry about this.
        """
        while self.remaining_bytes(buf) > 0:
            klass = BaseDescriptor.get_descriptor_class(buf.peekint(1))
            self.descriptors.append(klass(buf))

    @staticmethod
    def get_descriptor_class(tag):
        """maintains a map of descriptor tags and corresponding classes"""
        class_map = {
            0x03: EsDescriptor,
            0x04: DecoderConfigDescriptor,
        }
        if tag in class_map:
            return class_map[tag]
        return BaseDescriptor

    def get_descriptor_name(self):
        """Get the name of the descriptor. This is an incomplete implementation"""
        name_map = {
            0x03: "ES_Descriptor",
            0x04: "DecoderConfigDescriptor",
            0x05: "DecoderSpecificInfo",
            0x06: "SLConfigDescriptor",
        }
        if self.tag in name_map:
            return name_map[self.tag]

        return f"Decriptor {self.tag:02x}"

    def consumed_bytes(self, buf):
        """return the number of bytes consumed so far"""
        return buf.current_position() - self.start_position

    def remaining_bytes(self, buf):
        """get the number of unparsed bytes in this descriptor"""
        x = self.size + self.header_size - self.consumed_bytes(buf)
        if x < 0:
            raise AssertionError(f"{self} consumed={self.consumed_bytes(buf)}")
        return x

    def serialise(self):
        """Serialise the descriptor data into a dict object"""
        data = {"tag": self.tag, "size": self.size}
        if self.unhandled_bytes:
            data["data bytes"] = " ".join([f"{b:02x}" for b in self.unhandled_bytes])
        return data

    def add_optional_descriptors(self, data):
        """
        Add optional descriptors to the data.
        Subclasses overriding serialise can call this at the end of their own implementation.
        """
        for d in self.descriptors:
            data[d.get_descriptor_name()] = d.serialise()

    def __str__(self):
        return f"<{self.__class__.__name__}:{self.tag:02x} {self.size} bytes>"


class DecoderConfigDescriptor(BaseDescriptor):
    """Descriptor tag=0x04, signalled within ES_Descriptor"""

    def parse(self, buf):
        super().parse(buf)
        self.object_type = buf.readbyte()
        self.stream_type = buf.readbits(6)
        self.upstream = buf.readbits(1)
        buf.readbits(1)
        self.buffer_size_db = buf.readint(3)
        self.max_bit_rate = buf.readint32()
        self.avg_bit_rate = buf.readint32()

    def serialise(self):
        data = {
            "tag": self.tag,
            "size": self.size,
            "object_type": Tree(TreeType.ATTR, "object_type", self.object_type, self.oti_str()),
            "stream_type": self.stream_type,
            "upstream": self.upstream,
            "buffer_size": self.buffer_size_db,
            "max bit rate": self.max_bit_rate,
            "avg bit rage": self.avg_bit_rate,
        }

        self.add_optional_descriptors(data)
        return data

    def oti_str(self):
        """Get the description for object type identifier"""
        values = {
            0x00: "Forbidden",
            0x01: "Systems ISO/IEC 14496-1",
            0x02: "Systems ISO/IEC 14496-1",
            0x03: "Interaction Stream",
            0x04: "Systems ISO/IEC 14496-1 Extended BIFS Configuration",
            0x05: "Systems ISO/IEC 14496-1 AFX",
            0x06: "Font Data Stream",
            0x07: "Synthesized Texture Stream",
            0x08: "Streaming Text Stream",
            0x20: "Visual ISO/IEC 14496-2",
            0x21: "Visual ITU-T Recommendation H.264 | ISO/IEC 14496-10",
            0x22: "Parameter Sets for ITU-T Recommendation H.264 | ISO/IEC 14496-10",
            0x40: "Audio ISO/IEC 14496-3",
            0x60: "Visual ISO/IEC 13818-2 Simple Profile",
            0x61: "Visual ISO/IEC 13818-2 Main Profile",
            0x62: "Visual ISO/IEC 13818-2 SNR Profile",
            0x63: "Visual ISO/IEC 13818-2 Spatial Profile",
            0x64: "Visual ISO/IEC 13818-2 High Profile",
            0x65: "Visual ISO/IEC 13818-2 422 Profile",
            0x66: "Audio ISO/IEC 13818-7 Main Profile",
            0x67: "Audio ISO/IEC 13818-7 LowComplexity Profile",
            0x68: "Audio ISO/IEC 13818-7 Scaleable Sampling Rate Profile",
            0x69: "Audio ISO/IEC 13818-3",
            0x6A: "Visual ISO/IEC 11172-2",
            0x6B: "Audio ISO/IEC 11172-3",
            0x6C: "Visual ISO/IEC 10918-1",
            0x6D: "reserved for registration authority",
            0x6E: "Visual ISO/IEC 15444-1",
        }
        oti = self.object_type
        s = values[oti] if oti in values else "reserved/user private"
        return f"0x{oti:02x}: {s}"


class EsDescriptor(BaseDescriptor):
    """EE_descriptor, tag=0x03"""

    def parse(self, buf):
        super().parse(buf)
        self.esid = buf.readint16()
        self.stream_dependence_flag = buf.readbits(1)
        self.url_flag = buf.readbits(1)
        self.ocr_stream_flag = buf.readbits(1)
        self.stream_priority = buf.readbits(5)
        if self.stream_dependence_flag:
            self.depends_on_esid = buf.readint16()
        if self.url_flag:
            self.url_length = buf.readbyte()
            self.url = buf.readstr(self.url_length)
        if self.ocr_stream_flag:
            self.ocr_esid = buf.readint16()

    def serialise(self):
        data = {
            "tag": self.tag,
            "size": self.size,
            "esid": self.esid,
            "dependence_flag": self.stream_dependence_flag,
            "url_flag": self.url_flag,
            "ocr_stream_flag": self.ocr_stream_flag,
            "stream_priority": self.stream_priority,
        }

        if self.stream_dependence_flag:
            data["depends_on_esid"] = self.depends_on_esid

        self.add_optional_descriptors(data)
        return data
