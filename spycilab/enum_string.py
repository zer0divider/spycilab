from enum import Enum

class EnumString(Enum):
    def __str__(self):
        """
        This makes sure that whenever EnumClass.<enum> is used
         that we actually get the string and not "EnumClass.<enum>"
        :return:
        """
        return self.value
