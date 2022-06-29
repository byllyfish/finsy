# 🐟 Finsy 

Finsy is a P4Runtime controller framework written in Python using asyncio.

```python
import asyncio
import finsy as fy

async def main():
    sw1 = fy.Switch("sw1", "127.0.0.1:50001")
    async with sw1:
        print(sw1.p4info)

asyncio.run(main())
```

For more examples, see the examples directory.
