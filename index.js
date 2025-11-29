require("dotenv").config();
const {
  Client,
  GatewayIntentBits,
  PermissionsBitField,
  ChannelType
} = require("discord.js");
const mongoose = require("mongoose");

//=======================
// MONGO MODEL
//=======================
const GuildConfig = mongoose.model(
  "TempVoice",
  new mongoose.Schema({
    guildId: { type: String, required: true },
    hubChannelId: String,
    categoryId: String
  })
);

//=======================
// BOT CLIENT
//=======================
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildVoiceStates,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

//=======================
// CONNECT TO MONGO
//=======================
mongoose.connect(process.env.MONGO_URI).then(() => {
  console.log("Connected to MongoDB");
});

//=======================
// READY
//=======================
client.on("ready", () => {
  console.log(`${client.user.tag} is online!`);
});

//=======================
// SETUP COMMAND
//=======================
client.on("messageCreate", async message => {
  if (!message.guild) return;

  const args = message.content.split(" ");

  // .setup <voice_channel_id> <category_id>
  if (message.content.startsWith(".setup")) {
    if (!message.member.permissions.has(PermissionsBitField.Flags.Administrator))
      return message.reply("❌ خاصك صلاحيات الأدمن");

    const hub = args[1];
    const cat = args[2];

    if (!hub || !cat) return message.reply("❗ الاستعمال: `.setup <hubID> <categoryID>`");

    await GuildConfig.findOneAndUpdate(
      { guildId: message.guild.id },
      { hubChannelId: hub, categoryId: cat },
      { upsert: true }
    );

    message.reply("✅ تم حفظ الإعدادات بنجاح!");
  }

  //=======================
  // .v reject @user
  //=======================
  if (message.content.startsWith(".v reject")) {
    const user = message.mentions.members.first();
    if (!user) return message.reply("❗ منشن الشخص");

    if (!user.voice.channel)
      return message.reply("❌ هذا الشخص ليس داخل فويس");

    await user.voice.disconnect();
    message.reply(`✅ تم طرد **${user.user.username}** من الفويس`);
  }
});

//=======================
// TEMP VOICE CREATION
//=======================
client.on("voiceStateUpdate", async (oldState, newState) => {

  // User joins a voice
  if (!oldState.channel && newState.channel) {
    const config = await GuildConfig.findOne({ guildId: newState.guild.id });
    if (!config) return;

    if (newState.channel.id === config.hubChannelId) {
      const category = newState.guild.channels.cache.get(config.categoryId);

      const tempChannel = await newState.guild.channels.create({
        name: `${newState.member.user.username}'s Room`,
        type: ChannelType.GuildVoice,
        parent: category?.id
      });

      await newState.setChannel(tempChannel);
    }
  }

  // Delete empty temp channels
  if (oldState.channel && !newState.channel) {
    if (
      oldState.channel.parentId &&
      oldState.channel.members.size === 0
    ) {
      if (oldState.channel.name.endsWith("'s Room")) {
        setTimeout(() => {
          if (oldState.channel.members.size === 0) {
            oldState.channel.delete().catch(() => {});
          }
        }, 3000);
      }
    }
  }
});

//=======================
// LOGIN
//=======================
client.login(process.env.TOKEN);
