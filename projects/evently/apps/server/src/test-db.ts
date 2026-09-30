import { prisma } from '@evently/db'

const count = await prisma.user.count()

console.log('Server -> DB connection OK')
console.log('Users:', count)

await prisma.$disconnect()
