import { prisma } from './client.js'

async function main() {
  const usersCount = await prisma.user.count()

  console.log('Database connection OK')
  console.log('Users count:', usersCount)
}

main()
  .then(async () => {
    await prisma.$disconnect()
  })
  .catch(async (error) => {
    console.error(error)
    await prisma.$disconnect()
    process.exit(1)
  })
